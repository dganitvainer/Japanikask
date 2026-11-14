// Three-way control per filter: any / with / without (like st.radio in Streamlit)
const OPTIONS = [
  { value: "all", text: "הכל" },
  { value: "with", text: "עם" },
  { value: "without", text: "ללא" },
];

export default function FilterControl({ filter, value, onChange }) {
  return (
    <fieldset className={`filter state-${value}`}>
      <legend>
        <span aria-hidden="true">{filter.icon}</span> {filter.label}
      </legend>
      <div className="segments">
        {OPTIONS.map((o) => (
          <label key={o.value} className={`segment seg-${o.value}`}>
            <input
              type="radio"
              name={filter.id}
              value={o.value}
              checked={value === o.value}
              onChange={() => onChange(o.value)}
            />
            <span>{o.text}</span>
          </label>
        ))}
      </div>
    </fieldset>
  );
}
