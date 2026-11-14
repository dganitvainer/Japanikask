"""
eval_search.py – measures search quality

Each test query has a rule that defines up front which dishes are correct, based on the data itself
(e.g. "מרק חם" (hot soup) → every dish in the soups category). This keeps the score objective.

Run:
    venv/Scripts/python.exe eval_search.py            # comparison table of the variants
    venv/Scripts/python.exe eval_search.py --verbose  # plus the results of every query
    venv/Scripts/python.exe eval_search.py --sweep    # try different lexical weights

The index is built in memory only and never touches the app's chroma_db.
"""
import argparse
import sys

import chromadb
import pandas as pd
from chromadb.utils import embedding_functions

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from core.search_engine import (  # noqa: E402
    MODEL_NAME, build_document, build_metadata, search_collection,
)

CSV_PATH = "japanika_menu_enriched_complete.csv"
K = 5


# ---------- Rules that define a "correct answer" ----------
def has(col, *words):
    return lambda r: any(w in str(r[col]) for w in words)


def yes(col):
    return lambda r: str(r[col]).strip().startswith(("כן", "קל"))


def no(col):
    return lambda r: str(r[col]).strip().startswith("לא")


def all_of(*rules):
    return lambda r: all(rule(r) for rule in rules)


def any_of(*rules):
    return lambda r: any(rule(r) for rule in rules)


# (query as a waiter would type it, rule that identifies the correct dishes)
TEST_QUERIES = [
    # Taste / ingredient / dish type – the semantic search's job
    ("מרק חם", has("category", "מרקים")),
    ("משהו חריף עם עוף", all_of(yes("is_spicy"), has("protein_type", "עוף"))),
    ("סושי עם סלמון", all_of(has("category", "סושי"), has("protein_type", "סלמון"))),
    ("מנה עם בשר בקר", has("protein_type", "בקר")),
    ("נודלס", any_of(has("dish_name", "נודלס", "אטריות"), has("original_description", "נודלס", "אטריות"))),
    ("סלט קליל ורענן", has("category", "סלטים")),
    ("משהו מטוגן וקריספי", yes("is_fried")),
    ("מנה עם טופו", has("protein_type", "טופו")),
    ("לחמנייה רכה במילוי", has("category", "באן")),
    ("טונה נא", has("protein_type", "טונה")),
    ("סשימי", has("dish_name", "סשימי")),
    ("משהו עם בטטה", any_of(has("dish_name", "בטטה"), has("original_description", "בטטה"))),
    ("כיסונים", any_of(has("dish_name", "גיוזה", "וונטון", "כיסונ"), has("original_description", "כיסונ"))),
    ("סושי צמחוני", all_of(has("category", "סושי"), yes("is_vegetarian"))),
    ("משהו מוקפץ בווק", any_of(has("dish_name", "מוקפץ"), has("original_description", "מוקפץ", "ווק"))),
    # Attributes and negation – where vectors alone fail
    ("משהו טבעוני", yes("is_vegan")),
    ("סושי בלי דג נא", all_of(has("category", "סושי"), no("raw_fish"))),
    ("מנה לילד לא חריפה", all_of(yes("kid_friendly"), no("is_spicy"))),
    ("משהו ללא גלוטן", no("contains_gluten")),
]

# Holdout queries: written after the weight and synonyms were tuned, and nothing was tuned on them.
# If the score here is close to the score above, the improvement is real and not memorized.
HOLDOUT_QUERIES = [
    ("משהו עם אבוקדו", any_of(has("dish_name", "אבוקדו"), has("original_description", "אבוקדו"))),
    ("כנפיים", has("dish_name", "כנפיים")),
    ("רוטב טריאקי", any_of(has("dish_name", "טריאקי"), has("original_description", "טריאקי"))),
    ("משהו בטמפורה", any_of(has("dish_name", "טמפורה"), has("original_description", "טמפורה"))),
    ("סלט עם עוף", all_of(has("category", "סלטים"), has("protein_type", "עוף"))),
    ("משהו עם חלב קוקוס", any_of(has("original_description", "קוקוס"), has("semantic_description", "קוקוס"))),
    ("אדממה", has("dish_name", "אדממה")),
    ("משהו פיקנטי עם בקר", all_of(yes("is_spicy"), has("protein_type", "בקר"))),
    ("מנה עיקרית עם אורז", all_of(has("category", "עיקריות"), has("original_description", "אורז"))),
    ("ניגירי", has("dish_name", "ניגירי")),
    ("מנה עם שמנת", has("original_description", "שמנת")),
]


# ---------- Variants being compared ----------
def ranking_only(doc_fn):
    """Vector search only – no query understanding and no filters."""
    def run(col, query):
        res = col.query(query_texts=[query], n_results=K)
        return [m["dish_name"] for m in res["metadatas"][0]]
    return doc_fn, run


def full_pipeline():
    """Exactly what the app runs: query understanding → filters → hybrid ranking."""
    def run(col, query):
        out = search_collection(col, query, n_results=K, margin=10)  # large margin = no cutoff, for a fair comparison
        return [m["dish_name"] for m in out["results"][:K]]
    return build_document, run


VARIANTS = {
    "A: תיאור סמנטי בלבד (המצב המקורי)": ranking_only(lambda r: str(r["semantic_description"]).strip()),
    "B: + שם, קטגוריה ותיאור מהתפריט": ranking_only(build_document),
    "C: B + הבנת שאילתה ופילטרים (האפליקציה)": full_pipeline(),
}


def evaluate(df, doc_fn, run_fn, emb_fn, name, verbose=False, queries=None):
    queries = queries or TEST_QUERIES
    client = chromadb.EphemeralClient()
    col_name = f"eval_{abs(hash(name)) % 10**8}"
    try:
        client.delete_collection(col_name)
    except Exception:
        pass
    col = client.create_collection(col_name, embedding_function=emb_fn, metadata={"hnsw:space": "cosine"})
    col.add(
        documents=[doc_fn(r) for _, r in df.iterrows()],
        metadatas=[build_metadata(r) for _, r in df.iterrows()],
        ids=[str(i) for i in range(len(df))],
    )

    hit1 = mrr = prec = 0.0
    for query, rule in queries:
        relevant = {r["dish_name"] for _, r in df.iterrows() if rule(r)}
        got = run_fn(col, query)
        ranks = [i + 1 for i, g in enumerate(got) if g in relevant]
        first = ranks[0] if ranks else None
        hit1 += first == 1
        mrr += 1 / first if first else 0
        prec += len(ranks) / min(K, len(relevant)) if relevant else 0
        if verbose:
            mark = "✓" if first == 1 else ("~" if first else "✗")
            names = [("★" if g in relevant else "·") + g for g in got]
            print(f"  {mark} {query:<20} ({len(relevant):>2} נכונות)  " + " | ".join(names))

    n = len(queries)
    return {"hit@1": hit1 / n, "MRR": mrr / n, f"P@{K}": prec / n}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--verbose", action="store_true")
    ap.add_argument("--only", help="run only the variant starting with this letter (A/B/C)")
    ap.add_argument("--sweep", action="store_true", help="try different weights for the lexical score")
    ap.add_argument("--model", default=MODEL_NAME, help="embedding model to evaluate")
    args = ap.parse_args()

    df = pd.read_csv(CSV_PATH).fillna("")
    emb_fn = embedding_functions.SentenceTransformerEmbeddingFunction(model_name=args.model)

    if args.sweep:
        import core.search_engine as se
        doc_fn, run_fn = full_pipeline()
        print(f"{'LEXICAL_WEIGHT':<16}{'hit@1':>8}{'MRR':>8}{f'P@{K}':>8}")
        for w in [0, 0.25, 0.5, 0.75, 1.0, 1.5, 2.0]:
            se.LEXICAL_WEIGHT = w
            s = evaluate(df, doc_fn, run_fn, emb_fn, f"sweep{w}")
            print(f"{w:<16}{s['hit@1']:>8.2f}{s['MRR']:>8.2f}{s[f'P@{K}']:>8.2f}")
        return

    print(f"\nמודל: {args.model} | {len(df)} מנות")
    for title, queries in [("שאילתות פיתוח", TEST_QUERIES), ("מבחן חיצוני (holdout)", HOLDOUT_QUERIES)]:
        rows = []
        for name, (doc_fn, run_fn) in VARIANTS.items():
            if args.only and not name.startswith(args.only):
                continue
            if args.verbose:
                print(f"\n=== {title} | {name} ===")
            rows.append((name, evaluate(df, doc_fn, run_fn, emb_fn, name + title, args.verbose, queries)))

        print(f"\n{title} ({len(queries)} שאילתות)")
        print(f"{'גרסה':<44}{'hit@1':>8}{'MRR':>8}{f'P@{K}':>8}")
        for name, s in rows:
            print(f"{name:<44}{s['hit@1']:>8.2f}{s['MRR']:>8.2f}{s[f'P@{K}']:>8.2f}")


if __name__ == "__main__":
    main()
