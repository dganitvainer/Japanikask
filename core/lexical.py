"""
Lexical (word-match) score – complements the vector search.

A small embedding model knows few Hebrew words like "סשימי" (sashimi) or "כיסונים" (dumplings),
so a one-word query can return unrelated dishes. This module checks whether the query words
(or menu synonyms) appear in the dish name, category or description, and returns a score from 0 to 1.
"""
import re

# Menu vocabulary: what a customer says → how it is written on the menu
SYNONYMS = {
    "כיסונים": ["גיוזה", "וונטון", "כיסונ"],
    "כיסון": ["גיוזה", "וונטון", "כיסונ"],
    "לחמנייה": ["באן"],
    "לחמניה": ["באן"],
    "לחמניות": ["באן"],
    "כריך": ["באן", "סנדוויץ", "סנדויץ"],
    "ווק": ["מוקפץ", "ווק"],
    "מוקפץ": ["מוקפץ", "ווק"],
    "אטריות": ["נודלס", "אטריות"],
    "נודלס": ["נודלס", "אטריות"],
    "בשר": ["בקר"],
    "עוף": ["עוף", "צ׳יקן", "צ'יקן", "צי׳קן"],
    "רול": ["רול", "מאקי"],
    "סושי": ["סושי", "רול", "מאקי", "ניגירי", "סשימי"],
    "מרק": ["מרק", "מרקים"],
    "שרימפס": ["שרימפס", "חסילונים"],
}

# Fields and their weights: a match in the dish name is worth more than a match in the description
FIELDS = [("dish_name", 1.0), ("category", 1.0), ("protein_type", 0.7), ("original_description", 0.5)]

_PREFIXES = "והבלמשכ"


def _variants(token: str):
    """The word itself + without a Hebrew prefix (ו/ה/ב/ל...) + without a plural suffix + synonyms."""
    out = {token}
    if len(token) > 3 and token[0] in _PREFIXES:
        out.add(token[1:])
    for t in list(out):
        if len(t) > 4 and t.endswith(("ים", "ות")):
            out.add(t[:-2])
    for t in list(out):
        out.update(SYNONYMS.get(t, []))
    return out


def _norm(s: str) -> str:
    return str(s).replace("׳", "'").replace("’", "'")


def lexical_score(query_text: str, meta: dict) -> float:
    """
    Per-word score = the weight of the best field the word was found in.
    Final score = half the best-matching word + half the average:
    so "סלט קליל ורענן" (a light, fresh salad) isn't penalized for "light" and "fresh", which
    appear in no dish name, while a dish matching every word still scores higher.
    (Using max alone dropped the holdout score from 0.91 to 0.73.)
    """
    tokens = [t for t in re.split(r"[\s,.!?]+", _norm(query_text)) if len(t) >= 2]
    if not tokens:
        return 0.0
    fields = [(_norm(meta.get(f, "")), w) for f, w in FIELDS]
    per_token = []
    for tok in tokens:
        variants = [_norm(v) for v in _variants(tok)]
        per_token.append(max((w for text, w in fields if any(v in text for v in variants)), default=0.0))
    return 0.5 * max(per_token) + 0.5 * sum(per_token) / len(per_token)
