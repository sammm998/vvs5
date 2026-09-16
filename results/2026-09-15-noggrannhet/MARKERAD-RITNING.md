# Mängdarens egna streck mot läsningens rör

Fyra av korpusens blad har en **markerad ritning** vid sidan av facit: `marked.pdf`, med mängdarens egna
mätlinjer. Varje linje bär beteckningen i sitt ämne, längden i sitt innehåll och sträckan i sina punkter. Det
gör en annan sorts jämförelse möjlig än rad mot rad: **sträcka mot sträcka**, på ritningen.

Metoden: varje mätlinje provpunktas var tredje punkt, och för varje provpunkt frågas vad läsningen äger inom
fyra punkter. Svaret blir tre tal per beteckning - metrar vi äger under *samma* namn, under ett *annat* namn,
och metrar vi inte äger alls.

En fälla värd att nämna: tre av de fyra bladen är ritade stående och visas liggande (sidrotation 270).
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
| **summa** | **394,9** | **377,4 (95,6 %)** | **14,5 (3,7 %)** | **3,0 (0,8 %)** |

**Av varje meter mängdaren drog äger läsningen 95,6 % under samma beteckning.** Mindre än en procent är inte
ägt alls. Oenigheten handlar alltså nästan aldrig om *huruvida* något är ett rör - den handlar om *vilken
dimension* det är.

Och det är samma sak som rad-mot-rad-måttet säger med andra ord. Där stämmer bara 22 % av raderna inom ±10 %.
Båda talen är sanna och de mäter olika saker: en dimension som byter plats med sin granne flyttar knappt
någon meter i sträckjämförelsen, men slår sönder båda radernas summor. Det är därför summan kan ligga på 95 %
medan raderna inte gör det.

## Var de går isär, meter för meter

```
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
```


Varje rad ovan är en plats på ritningen där mängdaren drog ett streck och läsningen kallade det något annat:
DN110 som blev DN75, DN160 som blev DN110. Aldrig ett annat system, aldrig en vägg - alltid grannen i samma
stam. Det är dimensionsbytet, mätt geometriskt i stället för som en differens mellan två summor.

## Vad den här mätningen inte täcker

Fyra blad av femtionio. De övriga femtiofem har bara facits summor, inte mängdarens streck. De fyra är
dessutom korpusens starkaste (98, 100, 94 och 97 % täckning i radmåttet), så 95,6 % är ett svar om just dem -
inte om hela materialet. Kommer markerade ritningar för V- och W-serien går samma genomgång att köra där, och
då först vet vi om dimensionsbytet är hela felet eller bara det som syns här.
