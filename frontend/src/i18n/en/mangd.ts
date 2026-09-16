/* Mängdningen och granskningsrummet: tabellen, ritningen, beläggen, rättelserna
 *
 * En rad per sträng, svensk nyckel först. Saknas en rad visas svenskan.
 */
export const mangd: Record<string, string> = {
  "Beteckning": "Designation",
  "Etiketter": "Labels",
  "Horisontellt": "Horizontal",
  "Vertikalt": "Vertical",
  "Totalt": "Total",
  "Tvetydigt": "Ambiguous",
  "Skrafferat": "Hatched",
  "Stigare": "Risers",
  "Status": "State",
  "Sök beteckning/DN": "Search designation/DN",
  "Alla status": "All states",
  "okänt": "unknown",
  "BEKRÄFTAD": "CONFIRMED",
  "TVETYDIG": "AMBIGUOUS",
  "INGEN SKALA": "NO SCALE",
  "EJ STÖDD STIL": "UNSUPPORTED STYLE",
  "ENDAST STIGARE": "RISERS ONLY",
  "I SKRAFFERAD YTA": "IN HATCHED AREA",
  "Ritningen anger ingen höjd och inga stigare hittades": "The drawing states no height and no risers were found",
  "Stigarna är hittade; ange våningshöjd för att räkna om dem till meter":
    "The risers are found; set a storey height to turn them into metres",
};
