// Sends a search to the server (api.py). filters: { is_vegan: true, contains_gluten: false, ... }
// limit: how many results to return (the "show more" button asks for more)
export async function searchDishes(query, filters, limit = 10) {
  const res = await fetch("/api/search", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ query, filters, limit }),
  });
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  // { results: [...], total: N, understood: { text, filters } }
  return res.json();
}
