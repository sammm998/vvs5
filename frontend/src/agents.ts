/* Who does what in a reading, said once so the live film and the finished account never disagree.
 *
 * Each stage is a reader with one question. It answers from the drawing, hands the answer to the next, and the
 * numbers quoted are the ones the reading actually worked from - a frame off the film, not a retelling.
 */

export type Agent = { stage: string; who: string; title: string; asks: string };

export const AGENTS: Agent[] = [
  { stage: "READING_PDF", who: "Vektorläsaren", title: "Läser PDF:en", asks: "Vilka streck finns ritade, på vilka lager och med vilka pennor?" },
  { stage: "RECONSTRUCTING_TEXT", who: "Textbyggaren", title: "Bygger texten ur streck", asks: "Vilka av strecken är bokstäver, och vilka rader bildar de?" },
  { stage: "READING_DESIGNATIONS", who: "Beteckningsläsaren", title: "Läser beteckningarna", asks: "Vilka rader är beteckningar, och vilken dimension bär de?" },
  { stage: "FINDING_LEADERS", who: "Hänvisningsspåraren", title: "Följer hänvisningslinjerna", asks: "Vilken ritad linje utgår från vilken etikett, och var slutar den?" },
  { stage: "RESOLVING_PIPE_REPRESENTATION", who: "Familjeutredaren", title: "Avgör vad som är rör", asks: "Vilka pennor ritar rör på det här bladet, och vilka ritar byggnaden?" },
  { stage: "BUILDING_PHYSICAL_PIPES", who: "Rörbyggaren", title: "Bygger de fysiska rören", asks: "Vilka sträckor hör ihop till ett rör, och vem äger dem?" },
  { stage: "MEASURING", who: "Mätaren", title: "Mäter", asks: "Hur många meter blir det, i ritningens egen skala?" },
];

export const AGENT_SV: Record<string, string> = {
  scale: "Skalagranskaren", coverage: "Täckningsgranskaren", plausibility: "Rimlighetsgranskaren",
  topology: "Topologigranskaren", designation: "Beteckningsgranskaren", ocr_crosscheck: "OCR-korsprovet",
};

/* What a stage reports, from its own frame and - where the reading is finished - from the result it produced. */
export function frameSays(stage: string, f: any, result?: any): string[] {
  const c = result?.coverage ?? {};
  if (!f) return [];
  switch (stage) {
    case "READING_PDF":
      return [`${f.n_paths} ritade objekt på sidan, ${Math.round(f.page?.w ?? 0)} × ${Math.round(f.page?.h ?? 0)} punkter.`,
              "Inget är text ännu — en PDF från CAD skriver bokstäverna som streck."];
    case "RECONSTRUCTING_TEXT":
      return [`${f.n} textrader byggda ur strecken.`];
    case "READING_DESIGNATIONS":
      return [`${f.n} beteckningar lästa${c.with_dn != null ? `, ${c.with_dn} av dem med en dimension på raden` : ""}.`,
              "Vilka av dem som namnger rör avgör ritningens egen förklaringslista."];
    case "FINDING_LEADERS":
      return [`${f.n} hänvisningslinjer följda från etikett ut i ritningen.`,
              "Ingen linje uppfinns: bara streck ritningen faktiskt drar räknas."];
    case "RESOLVING_PIPE_REPRESENTATION": {
      const fams = f.families ?? [];
      return [`${fams.length} ritade familjer togs som rör${fams.length ? `: ${fams.map((x: any) => `penna ${x.width}`).join(", ")}` : ""}.`,
              "En familj som ingen beteckning når tas inte — den ritar då något annat."];
    }
    case "BUILDING_PHYSICAL_PIPES": {
      const out = [`${f.n} fysiska rör byggda.`];
      if (c.verified_attachments != null)
        out.push(`${c.verified_attachments} beteckningar möter sitt rör, ${c.ambiguous_attachments} är tvetydiga, ${c.no_attachments} når inget.`);
      return out;
    }
    case "MEASURING": {
      const s = result?.scale ?? f.scale ?? {};
      const tot = result?.totals?.confirmed_total_m ?? f.total_m ?? 0;
      const n = result?.quantities?.length ?? (f.quantities ?? []).length;
      return [`Skala ${s.state === "VERIFIED" ? "verifierad" : s.state ?? "okänd"}${s.meters_per_pdf_point ? ` — ${s.meters_per_pdf_point.toFixed(6)} m per punkt` : ""}.`,
              `${Number(tot).toFixed(2)} m bekräftad längd fördelad på ${n} beteckningar.`];
    }
  }
  return [];
}
