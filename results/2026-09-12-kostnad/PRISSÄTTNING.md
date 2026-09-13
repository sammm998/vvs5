# Prissättning i credits

Det här är plattformens prislista, vad den vilar på och vad den ger. Kostnaden per blad är uppmätt
(`KOSTNAD.md`, 296 blad); priset är satt ovanpå den så att en läsning alltid är billigare än en handmängdning
och så att marginalen bär det som inte står i kostnaden per blad: utveckling, support, hosting, moms.

## 1. Vad en credit köper

| Sida | Format | Credits |
|---|---|---:|
| A3 eller mindre (≤ 0,18 m²) | A3 | 1,0 |
| A2 | A2 | 1,0 |
| A1 | A1 | 2,0 |
| A0 | A0 | 3,0 |
| större än A0 | A0+ | 4,0 |

Ovanpå formatet ett **bläcktillägg**: 0,5 credits per påbörjade 30 000 banor utöver de första 30 000, högst
3,0 credits per sida. Ett normalt A1-blad (median 11 700 banor) betalar inget tillägg; ett blad med 1 084 301
banor (det tyngsta i korpusen) betalar taket.

En **andra blick med syn** på en sida kostar 1,0 credit och beställs för sig.

Ett nytt konto får **5 credits** att prova med. En läsning som inte ger en enda meter **betalas tillbaka** -
en skannad ritning, ett tomt blad, en handling utan rör är inte något kunden ska betala för.

## 2. Paketen

| Paket | Credits | Kr | Kr/credit | Räcker till (A1-blad) |
|---|---:|---:|---:|---:|
| Start | 25 | 249 | 9,96 | 12 |
| Kontor | 100 | 890 | 8,90 | 50 |
| Projekt | 500 | 3 900 | 7,80 | 250 |
| Storkund | 2 000 | 12 900 | 6,45 | 1 000 (faktureras) |

Priset per credit sjunker med volym; det per blad går från cirka 20 kr (Start) till cirka 13 kr (Storkund)
för ett A1-blad. En handmängdning av ett A1-blad tar en erfaren mängdare 1-3 timmar.

## 3. Vad bladet kostar tjänsten - och marginalen

Kostnadsmodellen är kalibrerad mot mätningen (`kostnad-sammanfattning.json`):

| | Uppmätt | I modellen (`COST_DEFAULTS`) |
|---|---:|---:|
| CPU per sida, fast | 17,4 s | 17,4 s |
| CPU per tusen banor | 1,47 s | 1,47 s |
| Kärntimme | 1,03 kr | 1,03 kr |
| Frågor till andra läsaren per sida | 1,7 + 0,048 per tusen banor | samma |
| En fråga | 0,052 kr | 0,052 kr |
| Lagring av utdata, tolv månader | ~0,03 kr | 0,03 kr |

Typblad (samma tabell som på adminsidan "Priser & credits"):

| Format | Banor | Credits | Kostnad kr | Marginal Start | Marginal Storkund |
|---|---:|---:|---:|---:|---:|
| A3 | 4 000 | 1,0 | 0,14 | 97 % | 96 % |
| A1 | 18 000 | 2,0 | 0,18 | 98 % | 97 % |
| A0 | 30 000 | 3,0 | 0,21 | 98 % | 97 % |
| A0+ | 60 000 | 4,5 | 0,30 | 98 % | 98 % |

Marginalen per blad är alltså i det närmaste hela intäkten: den rörliga kostnaden är öre, inte kronor. Det är
rätt slutsats, inte ett räknefel - motorn är deterministisk kod, och modellen (andra läsaren) kallas bara på
avgränsade frågor. Det som priset måste bära är det fasta: utveckling, support, försäljning, hosting (databas,
lager, domän, övervakning) och moms. Med 1 200 kr/mån för en maskin som klarar cirka 4 000 A1-blad i månaden
(40 % nyttjande) är hostingen per blad 0,30 kr; resten är människor.

## 4. Vad som händer i systemet

- **Offert innan läsning.** `GET /api/drawings/{id}/price` räknar sidorna (format, banor) och svarar med
  credits; projektet och ritningen visar taggen. Ett konto som saknar credits får 402 med vad som saknas, och
  läsningen startar inte.
- **Debitering vid start, avstämning vid slut.** Beloppet dras när läsningen köas (`charge_for_reading`).
  När den är klar (`settle_after_reading`) betalas allt tillbaka om ingen beteckning fick en meter.
- **Reskontra.** Varje rörelse är en rad i `credit_entries` (hundradels credits, med slag, referens och
  status). Köp är rader med belopp i öre och status `INVOICED` tills de bokförs; administratören ser dem.
- **Administratörer** debiteras inte. Prislistan och kostnadsmodellen ligger i `service_settings`
  (`price:list`, `cost:model`) och kan ändras på adminsidan utan driftsättning; marginaltabellen räknas om.
- **Publikt.** `/priser` läser `GET /api/public/pricing` - samma tal som debiteringen använder.

## 5. Antaganden att pröva mot verkligheten

1. Kortavgift 1,5 % (Storkund faktureras; övriga kort). 2. Modellpriset (0,02/0,08 kr per tusen token) - ändras
det ändras `llm_kr_per_question`. 3. Att kunden accepterar credits per blad snarare än per projekt: Projekt-
paketet finns för den som hellre köper en hel handling. 4. Att fem provcredits räcker för att visa värdet:
det är två A1-blad.
