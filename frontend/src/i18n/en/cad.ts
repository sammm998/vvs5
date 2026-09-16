/* CAD-rummen: mängdningsverktyget och byggmodellen
 *
 * En rad per sträng, svensk nyckel först. Saknas en rad visas svenskan.
 */
export const cad: Record<string, string> = {

  // --- blad, nivåer och vyer ------------------------------------------------------------------------------
  "Fil ▾": "File ▾",
  "+ Blad": "+ Sheet",
  "Nytt blad": "New sheet",
  "Inga egna blad ännu. Börja med ett tomt här ovanför.": "No sheets of your own yet. Start with an empty one above.",
  "Nivåer": "Levels",
  "Kopiera nivåns objekt till nivån ovanför": "Copy the level's objects to the level above",
  "Sektion A-A": "Section A-A",
  "Snittlinje y": "Section line y",
  "Ingenting i snittet.": "Nothing in the section.",
  "Fasad i stället": "Elevation instead",
  "Genomskinlighet i 3D": "Transparency in 3D",
  "Tråd": "Wireframe",
  "Visa PDF": "Show the PDF",
  "utskriven ritning": "printed drawing",
  "Öppna →": "Open →",
  "Mängda bladet →": "Take off the sheet →",
  "Inga revisioner än.": "No revisions yet.",
  "Källa": "Source",
  "Listan som CSV": "The list as CSV",

  // --- rita -----------------------------------------------------------------------------------------------
  "Ångra (Ctrl+Z)": "Undo (Ctrl+Z)",
  "Gör om (Ctrl+Y)": "Redo (Ctrl+Y)",
  "Ångra ritningen": "Undo the drawing",
  "Fångst": "Snap",
  "Fångst (F3)": "Snap (F3)",
  "Ortho (F8)": "Ortho (F8)",
  "Två punkter": "Two points",
  "Rektangulär": "Rectangular",
  "Cirkulär": "Circular",
  "Vänster": "Left",
  "Höger": "Right",
  "Lägg in": "Insert",
  "Skapa ett": "Create one",
  "höjd i mm": "height in mm",
  "– fri text –": "– free text –",
  "EI 60": "EI 60",
  "Disciplin att rita i": "Discipline to draw in",
  "pump, LA, WC…": "pump, AHU, WC…",

  // --- kollisioner och förslag ----------------------------------------------------------------------------
  "Inga kollisioner.": "No clashes.",
  "Godkänn": "Approve",
  "Godkänn alla": "Approve all",
  "Sök igen": "Search again",
  "Rita en fråga": "Draw a question",
  "Vad gäller frågan?": "What is the question about?",
  "t.ex. rita en vägg från (0,0) till (0,6000), 200 tjock, på Plan 0":
    "e.g. draw a wall from (0,0) to (0,6000), 200 thick, on Level 0",

  // --- import och mängder ---------------------------------------------------------------------------------
  "Ur en läst handling…": "From a read document set…",
  "Det som går att förstå blir byggobjekt, resten streck. DWG stöds inte - spara som DXF eller IFC.":
    "What can be understood becomes building objects, the rest strokes. DWG is not supported - save as DXF or IFC.",
  "Ur modellens egna mått. Servern räknar samma tal för exporten och kalkylen.":
    "From the model's own dimensions. The server computes the same numbers for the export and the costing.",
};
