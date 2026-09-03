export const STAGE_LABELS: Record<string, string> = {
  QUEUED: "Köad", RASTERISED_INPUT_OCR: "Skannad ritning: vektoriserar linjer och OCR-läser text", READING_PDF: "Läser PDF", DISCOVERING_DRAWING_GRAMMAR: "Upptäcker ritningsgrammatik", EXTRACTING_VECTORS: "Extraherar vektorer",
  RECONSTRUCTING_TEXT: "Rekonstruerar text", READING_DESIGNATIONS: "Läser beteckningar", FINDING_LEADERS: "Hittar hänvisningslinjer",
  RESOLVING_PIPE_REPRESENTATION: "Tolkar rörrepresentation", ATTACHING_PIPES: "Kopplar rör", BUILDING_TOPOLOGY: "Bygger topologi",
  BUILDING_PHYSICAL_PIPES: "Bygger fysiska rör", MEASURING: "Mäter", GENERATING_OVERLAYS: "Skapar markeringar", COMPLETED: "Klar", FAILED: "Misslyckades",
};

export function StatusBadge({ job }: { job: any }) {
  const cls = job.status === "COMPLETED" ? "ok" : job.status === "FAILED" ? "bad" : "warn";
  return <span className={`badge ${cls}`}>{STAGE_LABELS[job.stage] || job.stage}</span>;
}
