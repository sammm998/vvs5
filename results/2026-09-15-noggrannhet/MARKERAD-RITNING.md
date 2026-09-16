# Mängdarens egna streck mot läsningens rör

Fem av korpusens blad har en **markerad ritning** vid sidan av facit: `marked.pdf`, med mängdarens egna
mätlinjer. Varje linje bär beteckningen i sitt ämne, längden i sitt innehåll och sträckan i sina punkter. Det
gör en annan sorts jämförelse möjlig än rad mot rad: **sträcka mot sträcka**, på ritningen.

Metoden: varje mätlinje provpunktas var tredje punkt, och för varje provpunkt frågas vad läsningen äger inom
fyra punkter. Svaret blir tre tal per beteckning - metrar vi äger under *samma* namn, under ett *annat* namn,
och metrar vi inte äger alls.

En fälla värd att nämna: tre av bladen är ritade stående och visas liggande (sidrotation 270).
Annoteringarnas punkter står i det oroterade rummet. Utan sidans rotationsmatris hamnar mängdarens streck
någon annanstans än rören, och första körningen sa att nittio procent av deras mätning låg utanför vårt
ägande. Den siffran var min egen bugg, inte läsningens.

## Svaret

| blad | mängdarens m | samma namn | annat namn | inget ägande |
|---|---:|---:|---:|---:|
| A | 213,4 | **204,5 (96 %)** | 7,9 | 1,0 |
| C | 17,7 | **17,7 (100 %)** | 0,1 | 0,0 |
| D | 113,2 | **106,8 (94 %)** | 4,3 | 2,0 |
| E | 50,6 | **48,4 (96 %)** | 2,2 | 0,0 |
| W-50-1-A0133 | 305,0 | **169,8 (56 %)** | 74,6 | 60,6 |
| **summa** | **699,9** | **547,2 (78,2 %)** | **89,1 (12,7 %)** | **63,6 (9,1 %)** |

De fyra första bladen ligger på 94-100 procent. Det femte, som kom in sist och är det tätaste av dem, ligger
på 56 - och det är det bladet som är värt att läsa. Ett blad som stämmer säger bara att metoden fungerar där;
det här säger var den inte gör det, och med geometri i stället för summor att säga det med.

Två tal i A0133-raden ska läsas med ett förbehåll. 10,1 av "annat namn" är beteckningen
`VS1-S13-12 wallmounted`, som är samma rör som `VS1-S13-12/W` - mängdaren skriver monteringssättet i namnet
på den ena raden och inte på den andra, och sträckjämförelsen tar namnen som de står. Rad-mot-rad-måttet
(`facit_metrics.py`) viker ihop dem; här görs det inte, för att inte dölja något annat. Den verkliga
oenigheten om namn på bladet är alltså 64,5 m.

## Vad de 56 procenten består av

**36,5 m av `VS1-S13-35/W` äger vi som `VS1-S13-12/W`.** Läsningen har två rör på ~33 m som båda löper över
hela bladet - fram- och returledningen i samma krets. Det ena har två stöd och heter 35; det andra har ett
stöd och heter 12. Ett cirkulerande system är ett par, och båda linjerna bär samma beteckning. Bladet skriver
DN35 tre gånger och DN12 tjugo gånger, så när paret inte hålls ihop vinner den dimension som skrivits flest
gånger - oavsett vilken av dem som ritats längst. Samma fel står öppet på A0134 sedan tidigare.

**60,6 m är inte ägt alls**, mest `VS1-S13-12/W` 28,6, `VVC1-X7-16/W` 11,8, `VV1-X7-16/W` 9,8 och
`VP1-S13-42/W` 6,6. Det är öarna: ritat i rätt penna, utan att någon etikett når fram.

Båda är egna ändringar med egen grind, inte något att rätta i förbifarten.

## Var de går isär, meter för meter

```
blad med markerad ritning: A, C, D, E, W-50-1-A0133

=== A: 78 mätlinjer, skala 0.017639 m/pt
mängdarens beteckning   deras m    samma    annan    inget   vad vi kallade det
KV1-X31-16                 17.4     17.2      0.1      0.0   S3-R8-160 0.1, S3-R8-110 0.1
KV2-X31-16                 33.3     33.1      0.2      0.0   S3-R8-160 0.2, S3-R8-110 0.1
S1-P2-110                   9.8      9.8      0.0      0.0   
S1-P2-75                    4.8      3.8      0.5      0.4   S1-P2-110 0.3, S3-P2-160 0.2
S3-P2-160                  16.9     16.9      0.0      0.0   
S3-R8-110                  59.9     54.9      4.7      0.3   S3-R8-75 4.7, VV1-X31-16 0.1
S3-R8-160                  16.3     16.3      0.0      0.0   
S3-R8-75                   20.9     18.7      1.9      0.3   S3-R8-110 1.2, S3-R8-160 0.8
VV1-X31-16                 34.1     33.7      0.4      0.0   KV2-X31-16 0.2, KV1-X31-16 0.1, S3-R8-110 0.1, S3-R8-160 0.1
SUMMA                     213.4    204.5      7.9      1.0   (96 % samma namn, 0 % inget ägande)
=== C: 4 mätlinjer, skala 0.017639 m/pt
mängdarens beteckning   deras m    samma    annan    inget   vad vi kallade det
KV1-X31-16                 11.0     11.0      0.0      0.0   
S3-R8-75                    6.7      6.7      0.1      0.0   KV1-X31-16 0.1
SUMMA                      17.7     17.7      0.1      0.0   (100 % samma namn, 0 % inget ägande)
=== D: 36 mätlinjer, skala 0.017639 m/pt
mängdarens beteckning   deras m    samma    annan    inget   vad vi kallade det
D1-E4-110                   1.8      1.8      0.0      0.0   
FJV1-S6-50/W                4.1      2.0      0.0      2.0   
KV1-E13-75                 12.1     12.1      0.0      0.0   
KV1-E13-90                 12.1     12.1      0.1      0.0   S1-P2-110 0.1
S1-P2-110                  43.0     43.0      0.1      0.0   S1-P2-75 0.1
S1-P2-160                  24.8     21.3      3.4      0.0   S1-P2-110 3.4
S1-P2-75                   15.2     14.5      0.8      0.0   S1-P2-110 0.8
SUMMA                     113.2    106.8      4.3      2.0   (94 % samma namn, 2 % inget ägande)
=== E: 47 mätlinjer, skala 0.017639 m/pt
mängdarens beteckning   deras m    samma    annan    inget   vad vi kallade det
S1-P2-110                   9.3      9.2      0.0      0.0   S1-P2-75 0.0
S1-P2-160                  26.7     24.9      1.8      0.0   S1-P2-110 1.0, S1-P2-75 0.8
S1-P2-75                   14.6     14.3      0.4      0.0   S1-P2-160 0.4
SUMMA                      50.6     48.4      2.2      0.0   (96 % samma namn, 0 % inget ägande)
=== W-50-1-A0133: 216 mätlinjer, skala 0.017639 m/pt
mängdarens beteckning   deras m    samma    annan    inget   vad vi kallade det
KV1-X31-16                 31.3     31.2      0.1      0.0   KV1-X7-25/W 0.1, S2-P5-110 0.1
KV1-X7-16/W                16.8     16.8      0.0      0.0   
KV1-X7-20/W                 0.4      0.4      0.0      0.0   
KV1-X7-25/W                 3.5      3.4      0.1      0.0   KV1-X7-20/W 0.1
KV1-X7-32/W                 2.8      1.6      1.2      0.0   KV1-X7-16/W 0.6, KV1-X7-25/W 0.5
S2-P5-110                  10.7      9.9      0.8      0.0   S2-P5-75/75/50 0.6, KV1-X31-16 0.1
S2-P5-50                    2.6      1.7      0.9      0.0   S2-P5-110 0.8, S2-P5-75/75/50 0.1
S2-P5-75                    1.2      0.2      0.9      0.0   S2-P5-50 0.4, S2-P5-75/75/50 0.2, S2-P3-50 0.2, S2-P2-75 0.1
VP1-S13-42/W               13.2      6.6      0.0      6.6   
VS1-S13-12 wallmounted     10.4      0.0     10.1      0.4   VS1-S13-12/W 10.1
VS1-S13-12/W               76.2     41.7      6.0     28.6   VS1-X31-16 6.0
VS1-S13-15/W                2.5      0.0      2.1      0.4   VS1-S13-12/W 2.0, VS1-S13-22/W 0.1
VS1-S13-22/W                2.0      1.0      0.4      0.6   VS1-S13-12/W 0.4
VS1-S13-35/W               70.6     33.3     36.9      0.4   VS1-S13-12/W 36.5, VS1-S13-22/W 0.4
VS1-X31-16                  0.4      0.4      0.0      0.0   
VV1-X31-16                 19.6     14.1      5.6      0.0   VVC1-X7-16/W 3.0, VV1-X7-20/W 2.5
VV1-X7-16/W                16.5      0.0      6.7      9.8   VV1-X31-16 6.7
VV1-X7-20/W                 1.7      0.5      1.2      0.0   VV1-X7-25/W 1.2
VV1-X7-25/W                 5.7      3.3      0.4      2.0   VV1-X7-20/W 0.2, VV1-X31-16 0.1
VVC1-X7-16/W               16.8      3.7      1.4     11.8   VV1-X31-16 1.3, KV1-X31-16 0.0
SUMMA                     305.0    169.8     74.6     60.6   (56 % samma namn, 20 % inget ägande)
```
