/* Kamerans knappar. Egen komponent, för vyn ska kunna byta renderare utan att knapparna skrivs om. */
export type ViewName = "perspektiv" | "topp" | "front" | "sida";

const VIEWS: [ViewName, string][] = [
  ["perspektiv", "Perspektiv"],
  ["topp", "Ovanifrån"],
  ["front", "Framifrån"],
  ["sida", "Från sidan"],
];

export default function Drawing3DControls({ onView, onReset, exploded, onExploded }: {
  onView: (v: ViewName) => void;
  onReset: () => void;
  exploded: boolean;
  onExploded: (v: boolean) => void;
}) {
  return (
    <div className="d3-controls">
      <div className="seg">
        {VIEWS.map(([id, label]) => (
          <button key={id} onClick={() => onView(id)}>{label}</button>
        ))}
      </div>
      <button className="secondary small" onClick={onReset}>Återställ kameran</button>
      <label className="small check">
        <input type="checkbox" checked={exploded} onChange={(e) => onExploded(e.target.checked)} />
        {" "}Lyft rören ur planet
      </label>
      <span className="muted small d3-hint">Dra för att vrida · skift eller höger musknapp för att panorera · rulla för att zooma · klicka på ett rör</span>
    </div>
  );
}
