import Learn from "../components/Learn";

/* Akademin som egen plats, i hela fönstret.
 *
 * Analysen är ett arbetsbord: paneler, tabeller, en ritning att peta på. Att läsa sig till något är en annan
 * sysselsättning och tål inte samma form - den vill ha ro, en spalt att följa och ingenting i ögonvrån. Så
 * akademin tar hela fönstret, sätter sitt eget huvud högst upp och låter innehållet stå på en yta som är
 * papprets snarare än verktygets.
 */
export default function LearnPage() {
  return (
    <div className="academy">
      <div className="academy-sky" aria-hidden="true" />
      <header className="academy-bar">
        <span className="org">VVS-akademin</span>
        <span className="muted small">läs, öva, och pröva på en riktig ritning</span>
      </header>
      <div className="academy-scroll">
        <div className="academy-col">
          <Learn />
        </div>
      </div>
    </div>
  );
}
