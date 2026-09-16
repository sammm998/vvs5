# Klippbindningen: bevisad, och vad den säger

En PDF kan rita mer än den visar. CAD-exporten lägger ut hela xref:en och klipper bort det som ligger utanför
planens ram; det bortklippta finns kvar i filen som fullvärdig geometri. `engine/vvs_engine/pdf/extract.py`
läser `get_drawings()` utan `extended=True` och ser ingen klippning alls - alltså mäts rör som ingen ser.

## Provfallet

`data/dev/DRAWING_B.pdf` s.0, seqno 133, lager `V-56B--FE-_VS2x-`, bredd 1,44:

    sträcka (1547,76 , 115,48) -> (1553,88 , 114,28)
    rå längd    6,2365 pt
    synlig      0,0000 pt

Strecket ligger *inom* klippbanans bounding box men *utanför* dess sneda kant, så ett `scissor`-prov släpper
igenom det. Klippolygonen jag läste ur filen är identisk med den som angavs oberoende i uppdraget.

## Tre mätningar, två fel, och vad som fällde dem

| försök | klippbindning | dolt bläck | utfall |
|---|---|---:|---|
| 1 | ackumulerad stack av alla föregående klipp | 50,9 % | fel: nivåerna visar att stacken inte finns |
| 2 | senaste föregående klipp, fyrhörning läst ul,ur,ll,lr | 32,2 % | **fälld av renderaren** |
| 3 | senaste föregående klipp, fyrhörning läst ul,ur,lr,ll | **15,8 %** | **håller** |

Felet i försök 2 satt inte i bindningen utan i geometrin. PyMuPDF skriver en fyrhörning som ul, ur, ll, lr.
Läser man punkterna i den ordningen får man en rosett som korsar sig själv, med area 0 - och `buffer(0)`
"lagar" den till en fjärdedel av den rätta ytan. På ett klipp med verklig area 322 644 gav min läsning 80 661,
och tusentals synliga vägar såg dolda ut. Det är den sortens fel som en siffra aldrig avslöjar och en
rendering avslöjar direkt.

## Provet

Ett rutnät på 4 pt över bladet. Varje ruta får tre svar: bär rågeometrin bläck här, bär den klippta
geometrin bläck här, målar renderaren något här. De **omtvistade** rutorna är de där rågeometrin säger bläck
och den klippta säger tomt - där ska renderaren vara tom om bindningen är rätt.

Provets känslighet mäts samtidigt på rutorna där båda läsningarna är överens. Hittar provet inte bläck ens
där, bevisar dess tystnad ingenting, och utfallet blir OKONKLUSIVT i stället för ett godkännande.

    blad              dolt   dolda vägar   omtvistade rutor   varav bläck   känslighet   utfall
    DRAWING_A.pdf    0,00 %            0                  0             0       80,7 %   INGET KLIPPT
    DRAWING_B.pdf   15,83 %         2526               7452             0       97,5 %   HÅLLER
    DRAWING_C.pdf   11,62 %         2982               3343             2       95,0 %   HÅLLER

DRAWING_A har klippbanor men de döljer ingenting, så där finns inget att pröva - varken fel eller bevis.
På B och C målar renderaren i **0 respektive 2** av tillsammans 10 795 rutor som läsningen kallar dolda,
medan samma prov hittar bläck i 95-97,5 % av rutorna den kallar synliga. Tvåsidigt: provet ser bläck, och
det ser inget där vi säger att det inte ska finnas något.

## Vad som är dolt

På DRAWING_B är 2 526 vägar helt dolda och 84 delvis klippta, 15,8 % av bläcket. De tyngsta lagren:

    SK-46-P-0100-1764-A|SK-46C-B-EK-E   416
    V-56B--FE-_VS2x-                    324      <- VVS-rörlager
    SK-46-P-0100-1764-A|SK-46C-B-EI-E   222
    A-40-P-0100-1764-A|A-B-B-----N      137
    V-53BB-FE-_SFxx                     130

Dold geometri är alltså inte bara arkitektens underlag: 324 vägar ligger på ett rörlager och 130 på ett till.
Det är de metrarna Del 2 ska sluta räkna.

## Ordning

Verktyget är ett läsverktyg i `engine/tools/` och rör ingenting i motorn. Provfallets polygon är testdata,
inte produktionskod: ingen koordinat och inget filnamn från `data/dev/` finns i `vvs_engine/`.
