import { useEffect, useRef, useState } from "react";
import { searchDishes } from "./api.js";
import { FILTERS, describeFilter, toApiFilters } from "./filters.js";
import FilterControl from "./components/FilterControl.jsx";
import DishRow from "./components/DishRow.jsx";

const EXAMPLES = ["משהו חריף עם עוף", "סושי בלי דג נא", "מרק חם", "מנה לילד לא חריפה", "נודלס טבעוני"];
const initialFilters = Object.fromEntries(FILTERS.map((f) => [f.id, "all"]));
const PAGE_SIZE = 10; // results per page; "show more" adds another page

export default function App() {
  const [query, setQuery] = useState("");
  const [filters, setFilters] = useState(initialFilters);
  const [results, setResults] = useState(null); // null = no search yet
  const [total, setTotal] = useState(0); // how many relevant dishes exist (results may show fewer)
  const [understood, setUnderstood] = useState(null); // what the server detected in the text
  const [status, setStatus] = useState("idle"); // idle | loading | more | error
  const [filtersOpen, setFiltersOpen] = useState(false);
  const lastQuery = useRef("");

  const activeCount = Object.values(filters).filter((v) => v !== "all").length;

  async function run(q, f, limit = PAGE_SIZE) {
    const apiFilters = toApiFilters(f);
    if (!q.trim() && Object.keys(apiFilters).length === 0) {
      setResults(null);
      setUnderstood(null);
      return;
    }
    lastQuery.current = q;
    // A new search shows "loading"; "show more" keeps the current list on screen while it loads
    setStatus(limit > PAGE_SIZE ? "more" : "loading");
    try {
      const data = await searchDishes(q, apiFilters, limit);
      setResults(data.results);
      setTotal(data.total);
      setUnderstood(data.understood);
      setStatus("idle");
    } catch {
      setStatus("error");
    }
  }

  // Same search, one more page. The ranking is deterministic, so the dishes already
  // on screen stay in place and the new ones are added below them.
  function showMore() {
    run(lastQuery.current, filters, results.length + PAGE_SIZE);
  }

  // After the first search, changing a filter re-runs the same search
  useEffect(() => {
    if (results !== null || activeCount > 0) run(lastQuery.current, filters);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [filters]);

  function onSubmit(e) {
    e.preventDefault();
    run(query, filters);
  }

  function pickExample(text) {
    setQuery(text);
    run(text, filters);
  }

  return (
    <div className="page">
      <header className="masthead">
        <span className="brand">עוזר המלצרים</span>
        <span className="brand-sub">חיפוש מנות בתפריט לפי מה שהלקוח מתאר</span>
      </header>

      <form className="ask" onSubmit={onSubmit} role="search">
        <label htmlFor="q" className="ask-label">מה הלקוח מחפש?</label>
        <div className="ask-row">
          <input
            id="q"
            className="ask-input"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="למשל: סושי עם בטטה וקראנץ'"
            autoComplete="off"
            autoFocus
          />
          <button className="ask-button" type="submit" disabled={status === "loading"}>
            {status === "loading" ? "מחפש…" : "חיפוש"}
          </button>
        </div>
        {understood && Object.keys(understood.filters).length > 0 && (
          <div className="understood" aria-live="polite">
            <span className="understood-label">זיהיתי בבקשה:</span>
            {Object.entries(understood.filters).map(([id, value]) => {
              const d = describeFilter(id, value);
              return (
                <span key={id} className={`chip ${value ? "chip-with" : "chip-without"}`}>
                  <span aria-hidden="true">{d.icon}</span> {d.text}
                </span>
              );
            })}
            {understood.text && <span className="understood-rest">ומחפש לפי: "{understood.text}"</span>}
          </div>
        )}
      </form>

      <div className="layout">
        <aside className="filters" aria-label="פילטרים">
          <button
            type="button"
            className="filters-toggle"
            aria-expanded={filtersOpen}
            onClick={() => setFiltersOpen((o) => !o)}
          >
            פילטרים{activeCount > 0 && <span className="badge">{activeCount}</span>}
          </button>
          <div className={`filters-body ${filtersOpen ? "open" : ""}`}>
            {FILTERS.map((f) => (
              <FilterControl
                key={f.id}
                filter={f}
                value={filters[f.id]}
                onChange={(v) => setFilters((prev) => ({ ...prev, [f.id]: v }))}
              />
            ))}
            {activeCount > 0 && (
              <button type="button" className="clear" onClick={() => setFilters(initialFilters)}>
                ניקוי פילטרים
              </button>
            )}
          </div>
        </aside>

        <main className="results" aria-live="polite">
          {status === "error" && (
            <p className="notice error">
              השרת לא עונה. צריך להפעיל את api.py על פורט 8000 ולנסות שוב.
            </p>
          )}

          {status !== "error" && results === null && (
            <div className="empty">
              <p>
                אפשר לתאר טעם, מרקם או רכיב במילים של הלקוח. מגבלות כמו "בלי גלוטן" או "טבעוני"
                מזוהות אוטומטית והופכות לסינון מדויק.
              </p>
              <div className="examples">
                {EXAMPLES.map((ex) => (
                  <button key={ex} type="button" className="example" onClick={() => pickExample(ex)}>
                    {ex}
                  </button>
                ))}
              </div>
            </div>
          )}

          {status !== "error" && results !== null && results.length === 0 && (
            <p className="notice">
              לא נמצאו מנות לשילוב הזה. אפשר לנסח אחרת או להסיר פילטר.
            </p>
          )}

          {status !== "error" && results && results.length > 0 && (
            <>
              <p className="count">
                {total > results.length
                  ? `מציג ${results.length} מתוך ${total} מנות מתאימות`
                  : `${total} מנות מתאימות`}
              </p>
              <ol className="menu">
                {results.map((dish, i) => (
                  <DishRow key={`${dish.dish_name}-${i}`} dish={dish} />
                ))}
              </ol>
              {results.length < total && (
                <button type="button" className="more" onClick={showMore} disabled={status === "more"}>
                  {status === "more" ? "טוען…" : `הצג עוד ${Math.min(PAGE_SIZE, total - results.length)}`}
                </button>
              )}
            </>
          )}
        </main>
      </div>
    </div>
  );
}
