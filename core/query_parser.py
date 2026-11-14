"""
Query understanding: detects binary attributes in free text (vegan, spicy, gluten...) including
negation ("בלי", "ללא", "לא" = without / no / not) and turns them into exact filters.

Why: embedding models don't understand negation – the vector for "ללא גלוטן" (gluten-free)
is close to the vector for "גלוטן" (gluten). So these attributes are pulled out of the text and
handled as filters, and only the remaining text goes to the semantic search.

    >>> parse_query("סושי בלי דג נא ולא חריף")
    ParsedQuery(text='סושי', filters={'raw_fish': False, 'is_spicy': False})
"""
import re
from dataclasses import dataclass, field

# Optional negation word (possibly with the "ו" = "and" prefix) before the term
_NEG = r"(?:(?P<neg>ו?(?:בלי|ללא|לא|בלא|נטול|נטולת|נטולי|שאין\s+בה|שאין\s+בו))\s+)?"

# (column, regex for the term, value when not negated)
# Order matters: "דג נא" (raw fish) comes before "דג" (fish) so "בלי דג נא" doesn't exclude all fish
_RULES = [
    ("raw_fish",        r"דג(?:ים)?\s+נא(?:ים)?|סשימי\s+נא",           True),
    ("raw_fish",        r"נא(?:ים|ה)?",                                  True),   # "טונה נא", "סלמון נא" (raw tuna / raw salmon)
    ("raw_fish",        r"דג(?:ים)?\s+מבושל(?:ים)?",                    False),
    ("contains_fish",   r"דג(?:ים)?|פירות\s+ים",                        True),
    ("is_vegan",        r"טבעונ(?:י|ית|יים|יות)",                       True),
    ("is_vegetarian",   r"צמחונ(?:י|ית|יים|יות)",                       True),
    ("is_vegetarian",   r"בשר",                                          None),  # only "בלי בשר" (no meat) → vegetarian
    ("is_spicy",        r"חריפ(?:ה|ים|ות)|חריף|ספייסי|פיקנטי(?:ת)?",     True),
    ("contains_gluten", r"גלוטן",                                        True),
    ("contains_gluten", r"צליאק(?:ים)?|לצליאק(?:ים)?",                   False),
    ("contains_dairy",  r"חלב(?:י|ית)?(?!\s+(?:קוקוס|שקדים|סויה|אורז|שיבולת))|לקטוז|גבינה|גבינות",  True),
    ("contains_nuts",   r"אגוזים|בוטנים|אגוז",                           True),
    ("is_fried",        r"מטוגנ(?:ת|ים|ות)|מטוגן|בטיגון",                True),
    ("kid_friendly",    r"ל?ילד(?:ים|ה|ות)?|לקטנים",                     True),
]

# Words that carry no search meaning once the attributes are removed ("something", "dish", "with"...)
_STOPWORDS = {"משהו", "מנה", "מנות", "עם", "של", "שהוא", "שהיא", "שיהיה", "שיהיו", "בא", "לי",
              "רוצה", "מחפש", "מחפשת", "ו", "גם", "אבל", "וגם", "קצת", "מאוד", "בבקשה", "שמתאים",
              "שמתאימה", "מתאים", "מתאימה", "יש", "לכם", "למישהו", "מישהו", "עבור", "ל"}


@dataclass
class ParsedQuery:
    text: str
    filters: dict = field(default_factory=dict)


def parse_query(query: str) -> ParsedQuery:
    text = f" {query or ''} "
    filters = {}

    for col, term, positive in _RULES:
        # ו?/ה? – common prefixes ("and", "the"): "וחריף", "החריף"
        pattern = re.compile(rf"(?<!\S){_NEG}(?:ו|ה)?(?:{term})(?!\S)")
        for m in pattern.finditer(text):
            negated = bool(m.group("neg"))
            if col == "is_vegetarian" and positive is None:
                if not negated:
                    continue  # "עם בשר" (with meat) – left for the semantic search
                value = True  # "בלי בשר" (no meat) → vegetarian
            else:
                value = (not positive) if negated else positive
            filters.setdefault(col, value)
        text = pattern.sub(lambda m: " " if (col != "is_vegetarian" or positive is not None or m.group("neg")) else m.group(0), text)

    # "no fish" implies "no raw fish"; "דג מבושל" (cooked fish) is still fish
    if filters.get("contains_fish") is False:
        filters.setdefault("raw_fish", False)
    if re.search(r"דג(?:ים)?\s+מבושל", query or ""):
        filters.setdefault("contains_fish", True)

    words = []
    for w in re.split(r"[\s,.!?]+", text):
        # Leftover "ו" (and) prefix after an attribute was removed ("מטוגן וקריספי") – but not "וונטון"/"ווק"
        if len(w) > 3 and w[0] == "ו" and w[1] != "ו":
            w = w[1:]
        if w and w not in _STOPWORDS:
            words.append(w)
    return ParsedQuery(text=" ".join(words), filters=filters)
