import { useState } from "react";
import { DETAILS, isMaybe, isNo, isYes } from "../filters.js";

// Menu-style dish row: name ..... price. Clicking opens the description, flavors and allergens.
export default function DishRow({ dish }) {
  const [open, setOpen] = useState(false);
  const id = `dish-${dish.dish_name}`.replace(/\s+/g, "-");

  const tags = [];
  if (isYes(dish.is_spicy)) tags.push({ text: "חריף", kind: "chili" });
  if (isYes(dish.is_vegan)) tags.push({ text: "טבעוני", kind: "leaf" });
  else if (isYes(dish.is_vegetarian)) tags.push({ text: "צמחוני", kind: "leaf" });
  else if (isMaybe(dish.is_vegan)) tags.push({ text: "אפשר טבעוני", kind: "leaf" });
  if (isNo(dish.contains_gluten)) tags.push({ text: "ללא גלוטן", kind: "grain" });
  if (isYes(dish.raw_fish)) tags.push({ text: "דג נא", kind: "plain" });
  if (isYes(dish.kid_friendly)) tags.push({ text: "מתאים לילדים", kind: "plain" });

  const match = dish.relevance == null ? null : Math.max(0, Math.round(dish.relevance * 100));

  return (
    <li className={`dish ${open ? "open" : ""}`}>
      <button
        type="button"
        className="dish-head"
        aria-expanded={open}
        aria-controls={id}
        onClick={() => setOpen((o) => !o)}
      >
        <span className="dish-name">{dish.dish_name}</span>
        <span className="leader" aria-hidden="true" />
        <span className="dish-price">{dish.price}</span>
      </button>

      <div className="dish-meta">
        <span className="category">{dish.category}</span>
        {tags.map((t) => (
          <span key={t.text} className={`tag tag-${t.kind}`}>{t.text}</span>
        ))}
        {match !== null && (
          <span className="match" title="שילוב של דמיון במשמעות והתאמת מילים">התאמה {match}%</span>
        )}
      </div>

      {open && (
        <div className="dish-body" id={id}>
          <p>{dish.original_description || "אין תיאור בתפריט."}</p>
          {dish.flavor_profile && (
            <p className="flavor"><strong>פרופיל טעמים:</strong> {dish.flavor_profile}</p>
          )}
          <dl className="facts">
            {DETAILS.map(({ id: col, label }) => {
              const value = dish[col];
              if (!value) return null;
              const note = dish[`${col}_note`];
              const extra = note && note !== value && note.includes("–") ? note.split("–").slice(1).join("–").trim() : "";
              return (
                <div key={col} className={`fact fact-${isYes(value) ? "yes" : isNo(value) ? "no" : "maybe"}`}>
                  <dt>{label}</dt>
                  <dd>{value}{extra && <span className="fact-note"> ({extra})</span>}</dd>
                </div>
              );
            })}
          </dl>
        </div>
      )}
    </li>
  );
}
