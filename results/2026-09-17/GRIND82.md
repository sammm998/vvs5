# Grind 82: omfattningen inkopplad — ACCEPT, och en exakt nolla

Blint kört på 59 blad. Källan frusen före körningen: manifest `c96a81e87b9aa3a7`, commit `fffa36b`, noll
ändrade filer utanför commit. Grindfilen skriven utanför arbetskatalogen, så att ingen halvskriven fil kan
följa med i en commit under körningen.

## Förutsägelsen, skriven före körningen

Jag skrev innan grinden kördes att den skulle visa **ingenting**, och på angiven grund: inget blad i den här
korpusen bär en omfattningsmarkering. Sökt i 55 blads verkliga text - noll förekomster av BEFINTLIG, RIVAS,
PREFAB, DEMONTER och ARBETSOMR. (De 29 träffarna på RIVNING satt alla inne i ordet BESKRIVNING.)

## Utfallet

| | gate81 | gate82 | skillnad |
|---|---:|---:|---:|
| COVERAGE | 78,09 | 78,09 | 0 |
| FALSE_OWNERSHIP | 10,91 | 10,91 | 0 |
| TEXT_RECALL | 86,77 | 86,77 | 0 |
| FULL / PARTIAL / OVER / MISSED / WRONG | 187/201/153/163/65 | 187/201/153/163/65 | 0 |

Jämfört rad för rad i stället för bara på totalerna: **0 av 59 blad skiljer sig**, och summan är
10 157,364 m mot 10 157,364 m - skillnad **+0,000000**.

Och det som skulle tillkomma har tillkommit: **707 av 707 mängdrader bär en omfattning**, och bladraden i
`summary.json` redovisar antal och meter per omfattning.

## Beslut

**ACCEPT.** Läsningen har fått en åtskillnad utan att flytta en enda meter. Det är precis vad en första
inkoppling ska göra: dela upp talet, inte ändra det. Att dra bort befintligt ur en anbudsmängd är ett
affärsbeslut, inte något en tolk fattar åt någon.

Grinden bevisar inte att markeringarna LÄSES rätt - det finns inga i det här materialet att läsa. Den bevisar
att inkopplingen inte kostar något, och att varje rad nu har ett fält där svaret kan stå. Omfattningsläsningen
själv är prövad med tolv prov, däribland att en oförklarad markering blir OKAND_MARKERING och går till
granskning i stället för att tyst bli ny eller tyst försvinna.

Den biter på ombyggnadshandlingar. Den här korpusen är nybyggnad.

## Prov

845 gröna vid inkopplingen. Kontamineringsskannern PASS.
