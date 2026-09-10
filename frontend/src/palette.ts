/* Färgerna en beteckning har i hela produkten.
 *
 * Ett rör ska se likadant ut var det än visas: markerat på bladet, som prick i mängdtabellen, rest i 3D. Därför
 * bor paletten här och inte i den vy som råkade behöva den först. Nyckeln är rörets identitet - bas och
 * dimension - så samma rör får samma färg på varje blad i handlingen, och ingen färg är så mörk att den läses
 * som ritningens eget svarta streck.
 */
const PALETTE = ["#0d9a1a", "#0059e6", "#d91a1a", "#8c00b3", "#009999", "#cc7300", "#4d4de6", "#99591a",
                 "#e6007f", "#1a734d", "#808000", "#73bf00"];

export function identityColor(key: string): string {
  let h = 0;
  for (let i = 0; i < key.length; i++) h = (h * 31 + key.charCodeAt(i)) >>> 0;
  return PALETTE[h % PALETTE.length];
}
