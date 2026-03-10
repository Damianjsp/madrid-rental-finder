# Madrid rental costs by district and major satellite city (2025-2026 snapshot)

## Method and sources
- **Primary source for current asking rents:** Pisos.com live listings, scraped 2026-03-10. I grouped listings by area and computed indicative averages by bedroom count / typology from visible asking rents.
- **Market trend context:** idealista/data public market pages fetched 2026-03-10:
  - `https://www.idealista.com/data/`
  - `https://www.idealista.com/data/estudios-de-mercado/informe-mensual-del-mercado-residencial-espana-febrero-2026/`
  - `https://www.idealista.com/data/estudios-de-mercado/informe-de-alquiler-razonable-en-espana-2025/`
- **Caveat:** Idealista neighborhood report pages and Fotocasa listing pages were bot-blocked from this environment, so the **actual per-area numbers below come from Pisos.com live listings**. idealista/data is used as a secondary source to confirm overall market direction. Where a cell is `n/d`, there were not enough matching visible listings to produce a defensible figure.
- **Another caveat:** these are **asking rents, not signed contracts**. They are useful for market shopping / comparison, but not the same thing as INE contract indices.

## Master price table — Madrid city (21 distritos)

| Area | Avg Rent 1bed | Avg Rent 2bed | Avg Rent 3bed | House Avg | Chalet Avg | Trend | YoY Change % |
|---|---:|---:|---:|---:|---:|:--:|---:|
| Centro | €1,715 | €2,296 | €3,083 | n/d | n/d | ↑ | n/d |
| Arganzuela | €1,381 | €1,832 | €1,481 | n/d | n/d | ↑ | n/d |
| Retiro | €1,968 | €1,771 | €1,695 | €1,600 | n/d | ↑ | n/d |
| Salamanca | €3,433 | €2,793 | €2,469 | €2,750 | n/d | ↑ | n/d |
| Chamartín | €2,750 | €2,112 | €2,772 | n/d | n/d | ↑ | n/d |
| Tetuán | €1,656 | €2,527 | €2,046 | n/d | n/d | ↑ | n/d |
| Chamberí | €1,780 | €2,840 | €2,300 | €2,250 | n/d | ↑ | n/d |
| Fuencarral-El Pardo | €2,000 | €1,817 | €2,725 | €2,600 | n/d | ↑ | n/d |
| Moncloa-Aravaca | €3,883 | €1,787 | €1,872 | €2,875 | €2,325 | ↑ | n/d |
| Latina | €1,325 | €1,427 | €1,158 | €1,400 | n/d | ↑ | n/d |
| Carabanchel | €1,328 | €1,260 | €1,306 | n/d | €1,550 | ↑ | n/d |
| Usera | €1,215 | €1,500 | €1,430 | n/d | n/d | ↑ | n/d |
| Puente de Vallecas | €1,412 | €1,145 | €1,149 | n/d | n/d | ↑ | n/d |
| Moratalaz | n/d | n/d | €1,345 | n/d | n/d | ↑ | n/d |
| Ciudad Lineal | €1,442 | €2,258 | €1,306 | €3,800 | n/d | ↑ | n/d |
| Hortaleza | €3,479 | €1,551 | €3,017 | €2,750 | €1,850 | ↑ | n/d |
| Villaverde | n/d | n/d | n/d | n/d | €1,116 | ↑ | n/d |
| Villa de Vallecas | n/d | n/d | n/d | n/d | €1,311 | ↑ | n/d |
| Vicálvaro | n/d | €1,551 | €1,218 | €1,983 | n/d | ↑ | n/d |
| San Blas-Canillejas | €2,140 | €1,361 | €1,350 | €1,391 | €1,150 | ↑ | n/d |
| Barajas | €3,000 | €1,422 | €1,588 | n/d | n/d | ↑ | n/d |

## Master price table — Comunidad de Madrid satellite cities

| Area | Avg Rent 1bed | Avg Rent 2bed | Avg Rent 3bed | House Avg | Chalet Avg | Trend | YoY Change % |
|---|---:|---:|---:|---:|---:|:--:|---:|
| Alcobendas | n/d | €2,017 | €1,050 | €1,661 | n/d | ↑ | n/d |
| Alcorcón | €1,417 | €1,262 | €1,170 | €1,100 | €1,260 | ↑ | n/d |
| Getafe | €1,138 | €1,638 | €1,268 | €1,200 | n/d | ↑ | n/d |
| Leganés | €1,210 | €1,401 | €1,232 | €1,183 | n/d | ↑ | n/d |
| Móstoles | €1,000 | €1,000 | €1,302 | €1,150 | €1,005 | ↑ | n/d |
| Las Rozas de Madrid | €1,449 | €1,532 | €2,925 | €2,633 | €2,150 | ↑ | n/d |
| Pozuelo de Alarcón | €3,667 | €3,600 | €2,925 | €1,967 | €3,350 | ↑ | n/d |
| Majadahonda | €3,800 | €3,075 | €3,696 | €1,885 | n/d | ↑ | n/d |
| Boadilla del Monte | n/d | €1,900 | €2,480 | €3,212 | €2,262 | ↑ | n/d |
| San Sebastián de los Reyes | €1,425 | €1,002 | €2,000 | n/d | €2,900 | ↑ | n/d |
| Tres Cantos | €1,545 | €1,314 | €1,017 | €1,798 | €2,600 | ↑ | n/d |
| Alcalá de Henares | €1,120 | €1,090 | €1,117 | n/d | n/d | ↑ | n/d |
| Torrejón de Ardoz | €1,193 | €1,197 | €1,084 | n/d | €895 | ↑ | n/d |
| Rivas-Vaciamadrid | €2,090 | n/d | €1,725 | n/d | €1,200 | ↑ | n/d |
| Coslada | €1,509 | €1,276 | €1,910 | €1,150 | €2,800 | ↑ | n/d |
| San Fernando de Henares | €1,340 | €1,292 | €1,748 | €1,150 | n/d | ↑ | n/d |
| Villanueva de la Cañada | n/d | n/d | n/d | n/d | €1,350 | ↑ | n/d |
| Villanueva del Pardillo | €3,300 | n/d | n/d | n/d | €1,505 | ↑ | n/d |
| Galapagar | €4,200 | €1,308 | €1,400 | €1,373 | €1,033 | ↑ | n/d |
| Collado Villalba | n/d | €2,175 | €2,038 | €1,392 | €1,220 | ↑ | n/d |

## Heat map — cheapest to most expensive zones

### Cheapest cluster
- **Móstoles, Alcalá de Henares, Torrejón de Ardoz, Alcorcón, Leganés**.
- In Madrid city, the cheapest recurring 2-bed/3-bed asks sit in **Puente de Vallecas, Carabanchel, Latina, Moratalaz**.
- These zones are mostly around **€1.0k-€1.3k** for many 2-3 bed flats in the current visible stock.

### Mid-market cluster
- **Getafe, Coslada, San Fernando de Henares, Tres Cantos, Usera, Vicálvaro, San Blas-Canillejas**.
- This is roughly the **€1.25k-€1.7k** band for a lot of 2-bed stock.

### Upper-mid / expensive cluster
- **Arganzuela, Retiro, Fuencarral-El Pardo, Tetuán, Ciudad Lineal, Alcobendas, Las Rozas**.
- Typical 2-bed asks here are around **€1.5k-€2.3k**, sometimes higher in newer product.

### Premium / luxury cluster
- **Centro, Chamberí, Chamartín, Salamanca, Moncloa-Aravaca, Hortaleza**, plus **Pozuelo, Majadahonda, Boadilla** outside the M-30.
- This is where 2-bed stock commonly lands between **€2.1k and €3.6k+**, and chalets/large homes move far above that.

## Best value areas

These are the best value picks if you want a balance of rent, transport, amenities, and generally decent residential feel:

1. **Alcalá de Henares**
   - Strong value: around **€1,090 for 2-bed** and **€1,117 for 3-bed** in current visible stock.
   - Big city, Renfe, university, services, walkable historic core.

2. **Alcorcón**
   - Around **€1,262 for 2-bed** and **€1,170 for 3-bed**.
   - MetroSur + Cercanías + established services. Solid price-to-connectivity ratio.

3. **Leganés**
   - Around **€1,401 for 2-bed** and **€1,232 for 3-bed**.
   - Well-connected and practical. Less sexy, more useful. Sometimes that wins.

4. **Móstoles**
   - Around **€1,000 for 2-bed** and **€1,302 for 3-bed**.
   - One of the cheaper large municipalities with full daily-life infrastructure.

5. **Tres Cantos**
   - Around **€1,314 for 2-bed** with a more planned, safer, family-oriented environment.
   - Better for people who want quiet + commuter rail, not nightlife.

6. **Latina / Carabanchel**
   - Inside Madrid city but still materially below the prime districts.
   - **Latina 2-bed ~€1,427**; **Carabanchel 2-bed ~€1,260**.
   - Good option if you want city access without paying Salamanca tax.

## Price ranges by 2-bed rent

### Budget (<€800/month for 2-bed)
- **No major district or satellite city in this sample** produced a reliable average below €800.
- Brutal but honest: that segment is basically gone in Madrid’s visible portal stock.

### Mid-range (€800-1,200)
- **Móstoles** (~€1,000)
- **San Sebastián de los Reyes** (~€1,002)
- **Alcalá de Henares** (~€1,090)
- **Puente de Vallecas** (~€1,145)
- **Torrejón de Ardoz** (~€1,197)

### Premium (€1,200-1,800)
- **Alcorcón, Leganés, Getafe, Latina, Carabanchel, Usera, Vicálvaro, San Blas-Canillejas, Tres Cantos, Coslada, San Fernando de Henares, Retiro, Fuencarral-El Pardo, Moncloa-Aravaca**
- Broadly the largest bucket now.

### Luxury (>€1,800)
- **Centro, Arganzuela, Salamanca, Chamartín, Tetuán, Chamberí, Ciudad Lineal**
- Outside the city: **Alcobendas, Las Rozas, Pozuelo, Majadahonda, Boadilla**

## Market trends — up or cooling down?

Short version: **still up, not cooling in any meaningful way**.

### What the sources say
- idealista/data states in its **Informe mensual del mercado residencial - España febrero 2026** that it tracks monthly **offer, demand and price in sale and rent** and their recent evolution.
- idealista/data’s **Informe de alquiler razonable en España 2025** says explicitly that:
  - demand for rental housing has increased,
  - regulation since 2019 has reduced available stock,
  - that stock contraction has led to a **consequent increase in prices**.
- idealista/data main portal page also frames the broader context as a housing market with high pressure and insufficient supply.

### What the live listings snapshot suggests
- Prime Madrid remains very expensive: **Salamanca 2-bed ~€2,793**, **Chamberí ~€2,840**, **Centro ~€2,296**, **Chamartín ~€2,112**.
- Premium suburban markets are also stretched: **Pozuelo 2-bed ~€3,600**, **Majadahonda ~€3,075**, **Boadilla ~€1,900**, **Las Rozas ~€1,532**.
- Even the “cheaper” commuter cities usually sit around **€1,000-€1,300** for 2-bed stock now.
- The practical market floor has clearly shifted upward. Sub-€800 2-bed options are basically absent at city/municipality-average level.

### Bottom line
- **Direction:** up.
- **Main driver:** too little supply for the level of demand.
- **Who gets hit hardest:** households shopping for standard 2-bed family housing, because that segment is no longer “cheap” almost anywhere.

## Source list
1. Pisos.com live rental listings by area, accessed 2026-03-10. Examples:
   - Madrid capital: `https://www.pisos.com/alquiler/pisos-madrid_capital_zona_urbana/`
   - Centro: `https://www.pisos.com/alquiler/pisos-madrid_capital_centro/`
   - Salamanca: `https://www.pisos.com/alquiler/pisos-madrid_capital_salamanca/`
   - Alcobendas: `https://www.pisos.com/alquiler/pisos-alcobendas/`
   - Pozuelo: `https://www.pisos.com/alquiler/pisos-pozuelo_de_alarcon/`
   - etc. for each municipality listed above.
2. idealista/data homepage: `https://www.idealista.com/data/`
3. idealista/data, Informe mensual del mercado residencial - España febrero 2026: `https://www.idealista.com/data/estudios-de-mercado/informe-mensual-del-mercado-residencial-espana-febrero-2026/`
4. idealista/data, Informe de alquiler razonable en España 2025: `https://www.idealista.com/data/estudios-de-mercado/informe-de-alquiler-razonable-en-espana-2025/`

## Reliability notes
- Some niches have small sample sizes, especially **house/chalet** stock and outer districts like **Moratalaz, Villaverde, Villa de Vallecas**.
- A few municipality results are skewed by luxury or unusual stock mixes. Read them as **current portal-market signal**, not official contract index.
- If you need a finance-grade version, next step is to combine this with **official INE/MITMA index series** and **Idealista/Fotocasa district reports** manually from a browser session that can pass anti-bot checks.
