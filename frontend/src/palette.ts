/* Färgerna och tjocklekarna en beteckning har i hela produkten.
 *
 * Ett rör ska se likadant ut var det än visas: markerat på bladet, som prick i mängdtabellen, rest i 3D.
 * Därför bor paletten här och inte i den vy som råkade behöva den först.
 *
 * TVÅ STORHETER, TVÅ KANALER, och att det blev så är mätt och inte valt. Bladet bär både vilket SYSTEM ett rör
 * tillhör och vilken DIMENSION det har, och båda vill synas. Färgen räcker inte till båda:
 *
 *   - åtta toner är taket för vad som går att skilja åt när vilka två som helst kan mötas på samma blad
 *     (värsta par ΔE 19,3 normalseende, 10,7 vid färgblindhet - golven är 15 och 8). Tio toner ger 13,6 och
 *     tolv ger 12,4, alltså under golvet. Den gamla paletten hade tolv och innehöll par som `#4d4de6` mot
 *     `#0059e6`: ΔE 0,3 vid deuteranopi, praktiskt taget samma färg för den som inte skiljer rött från grönt;
 *   - att sedan stega ljusheten inom varje ton för dimensionen kollapsar alltihop. Prövat: ±0,03 i ljushet ger
 *     värsta par ΔE 1,4, och bredare steg gör det värre, inte bättre. Fyrtio färger går inte att skilja åt i
 *     det utrymme åtta nätt och jämnt får plats i.
 *
 * Alltså: **tonen bär systemet, tjockleken bär dimensionen.** Det är inte en kompromiss utan det som ritningen
 * själv gör - ett grövre rör ritas med grövre penna - och det är en kanal som annars stått oanvänd.
 *
 * NIVÅTALEN (`VG+1.74` och deras likar) får varken färg eller tjocklek, och det är avsiktligt. De varierar
 * LÄNGS ett rör - en självfallsledning faller - så de hör till etiketten på den punkt de står vid, inte till
 * stråket som helhet. Att färga ett helt stråk efter ett av dess nivåtal vore att påstå att röret ligger på en
 * enda nivå.
 *
 * Ingen färg är så mörk att den läses som ritningens eget svarta streck, och alla åtta når 3:1 mot papperet.
 */

/* Åtta toner, sökta fram och kontrollerade med databildsverktygets egen mätare (alla par, ljust läge):
 * ljushetsband PASS, kromagolv PASS, färgblindhet ΔE 10,7 PASS, normalseende ΔE 19,3 PASS, kontrast PASS. */
const PALETTE = ["#c44a7c", "#ffc94d", "#2e2270", "#0a5c0a", "#5aa0f0", "#00a300", "#8c00b3", "#57d3a6"];

/** Beteckningen ur en identitetsnyckel: `VS1-S13|DN22` och `VS1-S13|DN?` är samma namn och samma ton. */
export function colorKey(key: string): string {
  const cut = key.indexOf("|DN");
  return cut < 0 ? key : key.slice(0, cut);
}

/** Tonen ett rörnamn har. Samma namn ger samma ton i varje vy, varje blad och varje körning. */
export function identityColor(key: string): string {
  const name = colorKey(key);
  let h = 0;
  for (let i = 0; i < name.length; i++) h = (h * 31 + name.charCodeAt(i)) >>> 0;
  return PALETTE[h % PALETTE.length];
}

/** Dimensionen ur en identitetsnyckel, eller null när bladet inte skrev någon. */
export function dimensionOf(key: string): number | null {
  const cut = key.indexOf("|DN");
  if (cut < 0) return null;
  const n = Number(key.slice(cut + 3));
  return Number.isFinite(n) ? n : null;
}

/* Dimensionsband, inte rangordning inom bladet. En DN 110 ska se likadan ut på varje ritning, inte tjockast
 * på det blad där den råkar vara störst och tunnast på nästa. Banden följer de dimensioner svenska VVS-
 * handlingar faktiskt skriver. */
const BANDS = [20, 40, 75, 110];

/** Vilket av de fem dimensionsbanden en DN hör till. Okänd dimension hamnar i mitten. */
export function dimensionRank(dn: number | null): number {
  if (dn == null) return 2;
  for (let i = 0; i < BANDS.length; i++) if (dn <= BANDS[i]) return i;
  return BANDS.length;
}

/* Fem tjocklekar kring den enda som fanns förut (3,2), så att ett blad varken blir spindelväv eller sirap. */
const WIDTHS = [1.9, 2.5, 3.2, 4.1, 5.2];

/** Hur grovt ett rör ritas i överlägget, efter sin dimension. */
export function dimensionWidth(key: string): number {
  return WIDTHS[dimensionRank(dimensionOf(key))];
}

/** ...och hur grovt det ritas när det är valt: alltid tydligt grövre än sitt eget omarkerade streck. */
export function selectedWidth(key: string): number {
  return dimensionWidth(key) + 2.2;
}
