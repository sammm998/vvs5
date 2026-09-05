export const STAGE_LABELS: Record<string, string> = {
  QUEUED: "Köad", READING_PDF: "Läser PDF", RESOLVING_UNREADABLE_TEXT: "Löser olästa tecken med OCR", REVIEWING: "Granskar resultatet", DISCOVERING_DRAWING_GRAMMAR: "Upptäcker ritningsgrammatik", EXTRACTING_VECTORS: "Extraherar vektorer",
  RECONSTRUCTING_TEXT: "Rekonstruerar text", READING_DESIGNATIONS: "Läser beteckningar", FINDING_LEADERS: "Hittar hänvisningslinjer",
  RESOLVING_PIPE_REPRESENTATION: "Tolkar rörrepresentation", ATTACHING_PIPES: "Kopplar rör", BUILDING_TOPOLOGY: "Bygger topologi",
  BUILDING_PHYSICAL_PIPES: "Bygger fysiska rör", MEASURING: "Mäter", GENERATING_OVERLAYS: "Skapar markeringar", COMPLETED: "Klar", FAILED: "Misslyckades",
};

const STATUS_LABELS: Record<string, string> = { COMPLETED: "Klar", FAILED: "Misslyckades", RUNNING: "Kör", QUEUED: "Köad" };

export function StatusBadge({ job }: { job: any }) {
  const cls = job.status === "COMPLETED" ? "ok" : job.status === "FAILED" ? "bad" : "warn";
  // a finished job is described by its outcome, not by the stage it happened to stop on; and a stage we have
  // no word for still has a status we do
  const done = job.status === "COMPLETED" || job.status === "FAILED";
  const text = (done ? STATUS_LABELS[job.status] : STAGE_LABELS[job.stage]) || STATUS_LABELS[job.status] || "Okänt läge";
  return <span className={`badge ${cls}`}>{text}</span>;
}
