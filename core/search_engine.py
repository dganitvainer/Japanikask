import hashlib
import logging
import chromadb
import pandas as pd
from chromadb.utils import embedding_functions

from core.lexical import lexical_score
from core.query_parser import parse_query

log = logging.getLogger("search_engine")

# Multilingual model – handles Hebrew far better than Chroma's default embedding model
MODEL_NAME = "paraphrase-multilingual-MiniLM-L12-v2"
COLLECTION = "japanika_menu"

# Weight of the lexical (word-match) score relative to the vector score (chosen with eval_search.py)
LEXICAL_WEIGHT = 1.0

# Bump this when build_document or the normalization changes – the index is then rebuilt automatically
INDEX_VERSION = "3"

# Yes/no columns used for filtering. In the CSV they are free text ("כן – ציפוי פנקו", "לא – ציר"),
# so they are normalized to exactly three values: כן (yes) / לא (no) / אפשרי (maybe)
FLAG_COLUMNS = [
    "is_spicy", "contains_dairy", "contains_gluten", "contains_fish", "raw_fish",
    "contains_eggs", "contains_nuts", "contains_sesame", "is_vegan", "is_vegetarian",
    "is_fried", "kid_friendly",
]
_YES = ("כן", "קל", "חלקי")              # "קל" = mildly spicy, "כן/אפיה" = fried/baked, "חלקי" = partly fried
_MAYBE = ("אפשרי", "אולי", "לבחירה", "בינוני")


def normalize_flag(value) -> str:
    v = str(value).strip()
    if v.startswith("לא"):
        return "לא"
    if v.startswith(_YES):
        return "כן"
    if v.startswith(_MAYBE):
        return "אפשרי"
    return "לא ידוע"


def build_document(row) -> str:
    """The text that gets embedded. Leading with dish name and category helps queries like 'סשימי' or 'מרק'."""
    parts = [row["dish_name"], row["category"], row["original_description"], row["semantic_description"]]
    return ". ".join(str(p).strip() for p in parts if str(p).strip())


def build_metadata(row) -> dict:
    """All columns except the semantic description. Yes/no columns are normalized; the original text is kept in <col>_note."""
    meta = {k: str(v) for k, v in row.items() if k != "semantic_description"}
    for col in FLAG_COLUMNS:
        if col in meta:
            meta[f"{col}_note"] = meta[col]       # original text, for display
            meta[col] = normalize_flag(meta[col])  # clean value, for filtering
    return meta


class SearchEngine:
    _instance = None

    def __new__(cls, *args, **kwargs):
        # Singleton: the model and the database are loaded only once
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self, db_path="./chroma_db"):
        if self._initialized:
            return
        self.client = chromadb.PersistentClient(path=db_path)
        self.emb_fn = embedding_functions.SentenceTransformerEmbeddingFunction(model_name=MODEL_NAME)
        self.collection = None
        self._initialized = True

    # ---------- Indexing ----------
    def ensure_index(self, csv_path):
        """Builds the index only if it is missing, or if the CSV / document format changed since the last build."""
        fingerprint = self._fingerprint(csv_path)
        try:
            col = self.client.get_collection(COLLECTION, embedding_function=self.emb_fn)
            if (col.metadata or {}).get("fingerprint") == fingerprint and col.count() > 0:
                self.collection = col
                log.info("Index up to date (%d dishes)", col.count())
                return False
        except Exception:
            pass
        self.ingest_data(csv_path, fingerprint)
        return True

    @staticmethod
    def _fingerprint(csv_path):
        with open(csv_path, "rb") as f:
            return f"{INDEX_VERSION}-{MODEL_NAME}-{hashlib.md5(f.read()).hexdigest()[:12]}"

    def ingest_data(self, csv_path, fingerprint=None):
        df = pd.read_csv(csv_path).fillna("")

        # Dishes with no text produce an "average" vector that matches every query – skip them
        has_text = df["semantic_description"].astype(str).str.strip() != ""
        skipped = df.loc[~has_text, "dish_name"].tolist()
        df = df[has_text].reset_index(drop=True)
        if skipped:
            log.warning("Skipped %d dishes without semantic_description: %s", len(skipped), skipped)

        docs = [build_document(r) for _, r in df.iterrows()]

        metas = [build_metadata(r) for _, r in df.iterrows()]

        try:
            self.client.delete_collection(COLLECTION)
        except Exception:
            pass
        self.collection = self.client.create_collection(
            name=COLLECTION,
            embedding_function=self.emb_fn,
            metadata={"hnsw:space": "cosine", "fingerprint": fingerprint or self._fingerprint(csv_path)},
        )
        self.collection.add(documents=docs, metadatas=metas, ids=[f"id_{i}" for i in range(len(df))])
        log.info("Index rebuilt with %d dishes", len(df))

    # ---------- Search ----------
    def search(self, query_text, active_buttons=None, n_results=10, margin=0.25):
        return search_collection(self.collection, query_text, active_buttons, n_results, margin)


def build_where(filters):
    """True = 'with' (yes or maybe), False = 'without' (only dishes that definitely don't contain it)."""
    clauses = []
    for col, wanted in (filters or {}).items():
        if col not in FLAG_COLUMNS:
            continue
        if wanted is True:
            clauses.append({col: {"$in": ["כן", "אפשרי"]}})
        elif wanted is False:
            clauses.append({col: {"$eq": "לא"}})
    if not clauses:
        return None
    return clauses[0] if len(clauses) == 1 else {"$and": clauses}


def search_collection(collection, query_text, explicit_filters=None, n_results=10, margin=0.25):
    """
    Hybrid search:
      1. parse_query extracts binary attributes from the text ("בלי גלוטן", "טבעוני") → exact filters
      2. Filters chosen with the UI buttons override the ones detected in the text
      3. The remaining text is ranked by vector + lexical score among the dishes that passed the filters
      4. margin: only results close to the best one count as relevant, instead of always filling slots
      5. n_results: how many of the relevant dishes to return (the UI's "show more" asks for more)

    Returns: {"results": [...], "total": <number of relevant dishes>,
              "understood": {"text": ..., "filters": {...}}}
    """
    parsed = parse_query(query_text)
    filters = {**parsed.filters, **(explicit_filters or {})}
    where = build_where(filters)
    understood = {"text": parsed.text, "filters": parsed.filters}

    def page(relevant):
        return {"results": relevant[:n_results], "total": len(relevant), "understood": understood}

    # No text left, only filters: every dish that matches them is relevant
    if not parsed.text:
        if where is None:
            return page([])
        res = collection.get(where=where, include=["metadatas"])
        wanted = [col for col, v in filters.items() if v is True]
        # Definite "yes" matches first, then "maybe"; within each group sort by category and name
        ordered = sorted(
            res["metadatas"],
            key=lambda m: (sum(m.get(c) == "אפשרי" for c in wanted), m.get("category", ""), m.get("dish_name", "")),
        )
        return page([{**m, "relevance": None} for m in ordered])

    # The menu is small (~130 dishes), so every dish that passed the filters is ranked.
    # For a large menu: take the top-100 vector hits + matches from a lexical index (BM25).
    candidates = min(collection.count(), 300)
    res = collection.query(query_texts=[parsed.text], n_results=candidates, where=where)
    metas, dists = res["metadatas"][0], res["distances"][0]
    if not dists:
        return page([])

    scored = []
    for meta, dist in zip(metas, dists):
        vector = 1 - dist                                # similarity in meaning (cosine)
        lexical = lexical_score(parsed.text, meta)      # word match in name / category / description
        score = (vector + LEXICAL_WEIGHT * lexical) / (1 + LEXICAL_WEIGHT)
        scored.append((score, meta))
    scored.sort(key=lambda x: x[0], reverse=True)

    best = scored[0][0]
    relevant = [{**meta, "relevance": round(score, 4)} for score, meta in scored if score >= best - margin]
    return page(relevant)
