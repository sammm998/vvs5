/* Paletten, prövad utan webbläsare: tonen bär systemet, tjockleken bär dimensionen.
 * Buntas med esbuild och körs i node (se engine/tests/test_one_hue_one_system_one_width_one_size.py). */

import { colorKey, dimensionOf, dimensionRank, dimensionWidth, identityColor, selectedWidth } from "./palette";

let failed = 0;
function ok(what: string, cond: boolean) {
  console.log(`${cond ? "ok  " : "FEL "} ${what}`);
  if (!cond) failed++;
}

// ---------------------------------------------------------------- tonen hör till namnet, inte till måttet
ok("samma namn, samma ton oavsett dimension",
   identityColor("S1-P2|DN110") === identityColor("S1-P2|DN160")
   && identityColor("S1-P2|DN110") === identityColor("S1-P2|DN?"));
ok("olika namn får olika ton oftare än inte",
   new Set(["KV1-E13", "S1-P2", "VV1-X7", "VS1-S13", "FJV1-S6", "D1-E4"].map(identityColor)).size >= 5);
ok("beteckningen klipps ur nyckeln", colorKey("VS1-S13|DN22") === "VS1-S13" && colorKey("VS1-S13") === "VS1-S13");
ok("tonen är densamma i varje körning", identityColor("S1-P2|DN110") === identityColor("S1-P2|DN110"));

// ---------------------------------------------------------------- tjockleken hör till måttet
ok("dimensionen läses ur nyckeln", dimensionOf("S1-P2|DN110") === 110 && dimensionOf("S1-P2|DN?") === null
   && dimensionOf("S1-P2") === null);
ok("grövre rör ritas grövre",
   dimensionWidth("X|DN15") < dimensionWidth("X|DN50") && dimensionWidth("X|DN50") < dimensionWidth("X|DN110")
   && dimensionWidth("X|DN110") < dimensionWidth("X|DN160"));
ok("bandet är fast, inte rangordnat inom bladet: DN 110 ser likadan ut överallt",
   dimensionWidth("S1-P2|DN110") === dimensionWidth("KV1-E13|DN110"));
ok("okänd dimension hamnar i mitten och blir varken tunnast eller grövst",
   dimensionRank(null) === 2 && dimensionWidth("X|DN?") > dimensionWidth("X|DN15")
   && dimensionWidth("X|DN?") < dimensionWidth("X|DN160"));
ok("de tre dimensionerna på provbladet går att skilja åt",
   new Set(["S1-P2|DN75", "S1-P2|DN110", "S1-P2|DN160"].map(dimensionWidth)).size === 3);

// ---------------------------------------------------------------- det valda röret syns alltid
ok("valt rör är grövre än sitt eget omarkerade streck, i varje band",
   [null, 15, 32, 75, 110, 160].every((dn) => {
     const k = `X|DN${dn ?? "?"}`;
     return selectedWidth(k) > dimensionWidth(k);
   }));
// Urvalet bärs av FÄRGEN (röd), inte av tjockleken. Därför får ett valt tunt rör gärna vara smalare än ett
// omarkerat grovt - det som inte får hända är att tjockleken slutar visa dimensionen när röret väljs, för då
// döljer markeringen det man valde röret för att se.
ok("valt rör visar fortfarande sin dimension i tjockleken",
   selectedWidth("X|DN15") < selectedWidth("X|DN110")
   && selectedWidth("X|DN110") < selectedWidth("X|DN160"));

console.log(failed ? `\n${failed} PÅSTÅENDEN FÖLL` : "\nalla påståenden höll");
if (failed) process.exit(1);
