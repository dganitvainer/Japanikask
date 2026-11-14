// Sidebar filters. id = the CSV column name
export const FILTERS = [
  { id: "is_vegan", label: "טבעוני", icon: "🌱" },
  { id: "is_vegetarian", label: "צמחוני", icon: "🥗" },
  { id: "is_spicy", label: "חריף", icon: "🌶️" },
  { id: "contains_gluten", label: "גלוטן", icon: "🍞" },
  { id: "contains_dairy", label: "חלבי", icon: "🥛" },
  { id: "raw_fish", label: "דג נא", icon: "🐟" },
  { id: "is_fried", label: "מטוגן", icon: "🍤" },
  { id: "kid_friendly", label: "מתאים לילדים", icon: "👶" },
];

// Labels for every attribute the server can detect in the text (including ones without a button)
const LABELS = {
  ...Object.fromEntries(FILTERS.map((f) => [f.id, f])),
  contains_fish: { label: "דגים", icon: "🐟" },
  contains_nuts: { label: "אגוזים", icon: "🥜" },
};

// {is_vegan: true} → "טבעוני" (vegan), {contains_gluten: false} → "ללא גלוטן" (gluten-free)
export function describeFilter(id, value) {
  const f = LABELS[id] || { label: id, icon: "" };
  return { icon: f.icon, text: value ? f.label : `ללא ${f.label}` };
}

// Button state → what is sent to the server: "with" = true, "without" = false, "all" = not sent
export function toApiFilters(state) {
  const out = {};
  for (const [id, value] of Object.entries(state)) {
    if (value === "with") out[id] = true;
    if (value === "without") out[id] = false;
  }
  return out;
}

// The server normalizes every yes/no column to "כן" / "לא" / "אפשרי" (yes / no / maybe);
// the original text is in <col>_note
export const isYes = (v) => v === "כן";
export const isNo = (v) => v === "לא";
export const isMaybe = (v) => v === "אפשרי";

// Allergens and attributes shown in the dish details
export const DETAILS = [
  { id: "contains_gluten", label: "גלוטן" },
  { id: "contains_dairy", label: "חלב" },
  { id: "contains_eggs", label: "ביצים" },
  { id: "contains_nuts", label: "אגוזים" },
  { id: "contains_sesame", label: "שומשום" },
  { id: "contains_fish", label: "דג" },
  { id: "raw_fish", label: "דג נא" },
  { id: "is_spicy", label: "חריף" },
];
