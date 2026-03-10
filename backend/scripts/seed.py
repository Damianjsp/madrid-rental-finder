#!/usr/bin/env python3
"""
Seed reference data:
- portals
- districts
- neighborhoods (from safety-transport.md research)
- cost_benchmarks (from rental-costs.md research)

Run: python scripts/seed.py
"""

import logging
import sys
import os
from datetime import date

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from sqlalchemy import text
from mrf.db.session import get_db
from mrf.db.models import Portal, District, Neighborhood, CostBenchmark

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
log = logging.getLogger("seed")

SNAPSHOT_DATE = date(2026, 3, 10)
SOURCE = "pisos.com live listings + safety-transport research"

# ---------------------------------------------------------------------------
# Portals
# ---------------------------------------------------------------------------
PORTALS = [
    {"key": "spotahome", "name": "Spotahome", "tier": 1, "base_url": "https://www.spotahome.com"},
    {"key": "yaencontre", "name": "Yaencontre", "tier": 1, "base_url": "https://www.yaencontre.com"},
    {"key": "pisos", "name": "Pisos.com", "tier": 1, "base_url": "https://www.pisos.com"},
    {"key": "habitaclia", "name": "Habitaclia", "tier": 1, "base_url": "https://www.habitaclia.com"},
    {"key": "enalquiler", "name": "Enalquiler", "tier": 1, "base_url": "https://www.enalquiler.com"},
]

# ---------------------------------------------------------------------------
# Districts (Madrid city — 21 distritos + key municipalities as pseudo-districts)
# ---------------------------------------------------------------------------
DISTRICTS_MADRID = [
    "Centro", "Arganzuela", "Retiro", "Salamanca", "Chamartín",
    "Tetuán", "Chamberí", "Fuencarral-El Pardo", "Moncloa-Aravaca", "Latina",
    "Carabanchel", "Usera", "Puente de Vallecas", "Moratalaz", "Ciudad Lineal",
    "Hortaleza", "Villaverde", "Villa de Vallecas", "Vicálvaro",
    "San Blas-Canillejas", "Barajas",
]

# Satellite cities listed as municipalities (city != Madrid)
MUNICIPALITIES = [
    "Alcobendas", "Alcorcón", "Getafe", "Leganés", "Móstoles",
    "Las Rozas de Madrid", "Pozuelo de Alarcón", "Majadahonda",
    "Boadilla del Monte", "San Sebastián de los Reyes", "Tres Cantos",
    "Alcalá de Henares", "Torrejón de Ardoz", "Rivas-Vaciamadrid",
    "Coslada", "San Fernando de Henares", "Villanueva de la Cañada",
    "Villanueva del Pardillo", "Galapagar", "Collado Villalba",
    "Torrelodones", "Fuenlabrada", "Parla",
]

# ---------------------------------------------------------------------------
# Neighborhoods (from safety-transport.md)
# Area | District/City | Safety | commute_min | commute_max | zone
# sol_min, sol_max, atocha_min, atocha_max inferred from "Time to Sol/Atocha"
# ---------------------------------------------------------------------------
# Format: (name, district_name, municipality, safety_score, transport_score,
#          sol_min, sol_max, atocha_min, atocha_max, zone, notes)
NEIGHBORHOODS = [
    # Madrid city neighborhoods
    ("Salamanca (Recoletos/Goya/Lista)", "Salamanca", "Madrid", 5, 5, 10, 20, 10, 20, "A",
     "L2/L4/L5/L6/L9/L10 — Serrano, Goya, Príncipe de Vergara"),
    ("Chamberí (Almagro/Ríos Rosas/Trafalgar)", "Chamberí", "Madrid", 5, 5, 10, 20, 10, 20, "A",
     "L1/L2/L4/L5/L7/L10"),
    ("Retiro (Ibiza/Estrella/Niño Jesús)", "Retiro", "Madrid", 5, 5, 10, 20, 10, 20, "A",
     "L2/L6/L9 — Ibiza, Sainz de Baranda"),
    ("Chamartín (El Viso/Hispanoamérica)", "Chamartín", "Madrid", 5, 5, 10, 20, 10, 20, "A",
     "L9/L10 + C1/C2/C3/C4/C7/C8/C10 at Nuevos Ministerios/Chamartín"),
    ("Argüelles/Moncloa", "Moncloa-Aravaca", "Madrid", 4, 4, 10, 20, 10, 20, "A",
     "L3/L6 — Moncloa/Argüelles"),
    ("Pacífico/Adelfas", "Retiro", "Madrid", 4, 4, 15, 25, 15, 25, "A",
     "L1/L6 + C1/C2/C7/C10 near Méndez Álvaro/Delicias"),
    ("Delicias/Legazpi", "Arganzuela", "Madrid", 4, 4, 15, 25, 15, 25, "A",
     "L3/L6 + C1/C10 Delicias"),
    ("Madrid Río / Imperial", "Arganzuela", "Madrid", 4, 4, 15, 25, 15, 25, "A",
     "L5/L6/L10 + C1/C7/C10 Príncipe Pío"),
    ("Valdezarza/Peñagrande", "Fuencarral-El Pardo", "Madrid", 4, 3, 25, 35, 25, 35, "A",
     "L7"),
    ("Mirasierra/Paco de Lucía", "Fuencarral-El Pardo", "Madrid", 4, 4, 25, 35, 25, 35, "A",
     "L9 + C7/C8 Paco de Lucía"),
    ("Arturo Soria", "Ciudad Lineal", "Madrid", 4, 3, 20, 35, 20, 35, "A",
     "L4"),
    ("Sanchinarro", "Hortaleza", "Madrid", 4, 4, 25, 40, 25, 40, "A",
     "L1 (ML1 nearby) + C4 Fuente de la Mora"),
    ("Las Tablas", "Fuencarral-El Pardo", "Madrid", 4, 3, 25, 40, 25, 40, "A",
     "L10 + C4 Fuencarral/Chamartín"),
    ("Valdebebas", "Hortaleza", "Madrid", 4, 4, 25, 35, 35, 45, "A",
     "L8 + C1/C10 Valdebebas"),
    ("Conde de Orgaz", "Hortaleza", "Madrid", 4, 3, 25, 40, 25, 40, "A",
     "L4/L5 Canillas"),
    ("Carabanchel (Opañel/Comillas)", "Carabanchel", "Madrid", 3, 3, 25, 40, 25, 40, "A",
     "L5/L6"),
    ("Usera (Almendrales/Pradolongo)", "Usera", "Madrid", 2, 3, 20, 35, 20, 35, "A",
     "L6 Usera + L3 San Fermín + C5 Doce de Octubre"),
    ("Puente de Vallecas", "Puente de Vallecas", "Madrid", 2, 3, 20, 40, 20, 40, "A",
     "L1 + C2/C7/C8 Entrevías"),
    ("Villaverde Alto", "Villaverde", "Madrid", 2, 3, 25, 40, 25, 40, "A",
     "L3 + C4/C5 Villaverde Alto"),
    ("Lavapiés/Embajadores", "Centro", "Madrid", 2, 4, 5, 15, 5, 15, "A",
     "L3/L5 Embajadores + C5"),
    ("Sol/Gran Vía/Callao", "Centro", "Madrid", 3, 5, 0, 10, 0, 10, "A",
     "L1/L2/L3/L5/L10"),
    ("Tetuán (Cuatro Caminos)", "Tetuán", "Madrid", 3, 4, 10, 25, 10, 25, "A",
     "L1/L2/L6"),
    ("Villaverde Bajo / San Cristóbal", "Villaverde", "Madrid", 1, 2, 25, 40, 25, 40, "A",
     "L3 San Cristóbal + C3/C4 San Cristóbal Industrial"),
    ("Puerta del Ángel / Lucero", "Latina", "Madrid", 3, 3, 20, 35, 20, 35, "A",
     "L6 + C1/C7/C10 Príncipe Pío nearby"),
    # Satellite cities
    ("Pozuelo (Estación)", "Pozuelo de Alarcón", "Pozuelo de Alarcón", 5, 4, 20, 30, 20, 30, "B1",
     "ML2/ML3 + C7/C10 Pozuelo"),
    ("Pozuelo (Prado de Somosaguas)", "Pozuelo de Alarcón", "Pozuelo de Alarcón", 5, 3, 35, 45, 35, 45, "B1",
     "ML2"),
    ("Majadahonda", "Majadahonda", "Majadahonda", 5, 4, 25, 35, 25, 35, "B2",
     "C7/C10 Majadahonda"),
    ("Las Rozas", "Las Rozas de Madrid", "Las Rozas de Madrid", 5, 4, 25, 40, 25, 40, "B2",
     "C7/C10 Las Rozas"),
    ("Torrelodones", "Torrelodones", "Torrelodones", 4, 3, 35, 45, 35, 45, "B2",
     "C8/C10 Torrelodones"),
    ("Tres Cantos", "Tres Cantos", "Tres Cantos", 5, 4, 30, 40, 30, 40, "B1",
     "C4 Tres Cantos"),
    ("Alcobendas (La Moraleja)", "Alcobendas", "Alcobendas", 5, 3, 35, 50, 35, 50, "B1",
     "L10 La Granja/Marqués de la Valdavia"),
    ("Alcobendas (Centro)", "Alcobendas", "Alcobendas", 4, 4, 30, 45, 30, 45, "B1",
     "L10 + C4 Valdelasfuentes"),
    ("San Sebastián de los Reyes", "San Sebastián de los Reyes", "San Sebastián de los Reyes", 4, 3, 35, 50, 35, 50, "B1",
     "L10 Baunatal/Reyes Católicos"),
    ("Rivas-Vaciamadrid", "Rivas-Vaciamadrid", "Rivas-Vaciamadrid", 4, 3, 35, 50, 35, 50, "B1",
     "L9"),
    ("Coslada", "Coslada", "Coslada", 3, 4, 20, 30, 20, 30, "B1",
     "L7 + C2/C7 Coslada/San Fernando"),
    ("San Fernando de Henares", "San Fernando de Henares", "San Fernando de Henares", 3, 4, 25, 35, 25, 35, "B1",
     "L7 + C2 San Fernando"),
    ("Torrejón de Ardoz", "Torrejón de Ardoz", "Torrejón de Ardoz", 3, 3, 25, 35, 25, 35, "B2",
     "C2/C7 Torrejón"),
    ("Alcalá de Henares", "Alcalá de Henares", "Alcalá de Henares", 3, 3, 35, 45, 35, 45, "B3",
     "C2/C7 Alcalá/La Garena"),
    ("Getafe (Sector 3)", "Getafe", "Getafe", 4, 4, 20, 30, 20, 30, "B1",
     "L12 + C4 Getafe Sector 3"),
    ("Getafe (Centro)", "Getafe", "Getafe", 3, 4, 20, 30, 20, 30, "B1",
     "L12 + C4 Getafe Centro"),
    ("Leganés (Zarzaquemada)", "Leganés", "Leganés", 3, 4, 20, 30, 20, 30, "B1",
     "L12 + C5 Zarzaquemada"),
    ("Leganés (Centro)", "Leganés", "Leganés", 3, 4, 20, 35, 20, 35, "B1",
     "L12 + C5 Leganés"),
    ("Alcorcón (Retamas)", "Alcorcón", "Alcorcón", 4, 4, 20, 35, 20, 35, "B1",
     "L12 + C5 Las Retamas"),
    ("Alcorcón (Central)", "Alcorcón", "Alcorcón", 3, 4, 20, 35, 20, 35, "B1",
     "L10+L12 Puerta del Sur + C5 Alcorcón"),
    ("Móstoles (El Soto)", "Móstoles", "Móstoles", 3, 3, 25, 40, 25, 40, "B2",
     "L12 + C5 Móstoles-El Soto"),
    ("Móstoles (Central)", "Móstoles", "Móstoles", 3, 3, 30, 45, 30, 45, "B2",
     "L12 + C5 Móstoles"),
    ("Boadilla del Monte", "Boadilla del Monte", "Boadilla del Monte", 5, 2, 35, 55, 35, 55, "B2",
     "ML3"),
    ("Fuenlabrada", "Fuenlabrada", "Fuenlabrada", 2, 3, 25, 45, 25, 45, "B2",
     "L12 + C5 Fuenlabrada"),
    ("Parla", "Parla", "Parla", 2, 3, 30, 50, 30, 50, "B2",
     "Tranvía Parla + C4 Parla"),
]

# ---------------------------------------------------------------------------
# Cost benchmarks (from rental-costs.md)
# ---------------------------------------------------------------------------
COST_BENCHMARKS_DISTRICTS = [
    # (scope_name, avg_1bed, avg_2bed, avg_3bed, avg_house, avg_chalet)
    ("Centro",              1715,  2296,  3083,  None, None),
    ("Arganzuela",          1381,  1832,  1481,  None, None),
    ("Retiro",              1968,  1771,  1695,  1600, None),
    ("Salamanca",           3433,  2793,  2469,  2750, None),
    ("Chamartín",           2750,  2112,  2772,  None, None),
    ("Tetuán",              1656,  2527,  2046,  None, None),
    ("Chamberí",            1780,  2840,  2300,  2250, None),
    ("Fuencarral-El Pardo", 2000,  1817,  2725,  2600, None),
    ("Moncloa-Aravaca",     3883,  1787,  1872,  2875, 2325),
    ("Latina",              1325,  1427,  1158,  1400, None),
    ("Carabanchel",         1328,  1260,  1306,  None, 1550),
    ("Usera",               1215,  1500,  1430,  None, None),
    ("Puente de Vallecas",  1412,  1145,  1149,  None, None),
    ("Moratalaz",           None,  None,  1345,  None, None),
    ("Ciudad Lineal",       1442,  2258,  1306,  3800, None),
    ("Hortaleza",           3479,  1551,  3017,  2750, 1850),
    ("Villaverde",          None,  None,  None,  None, 1116),
    ("Villa de Vallecas",   None,  None,  None,  None, 1311),
    ("Vicálvaro",           None,  1551,  1218,  1983, None),
    ("San Blas-Canillejas", 2140,  1361,  1350,  1391, 1150),
    ("Barajas",             3000,  1422,  1588,  None, None),
]

COST_BENCHMARKS_MUNICIPALITIES = [
    # (scope_name, avg_1bed, avg_2bed, avg_3bed, avg_house, avg_chalet)
    ("Alcobendas",              None,  2017,  1050,  1661, None),
    ("Alcorcón",                1417,  1262,  1170,  1100, 1260),
    ("Getafe",                  1138,  1638,  1268,  1200, None),
    ("Leganés",                 1210,  1401,  1232,  1183, None),
    ("Móstoles",                1000,  1000,  1302,  1150, 1005),
    ("Las Rozas de Madrid",     1449,  1532,  2925,  2633, 2150),
    ("Pozuelo de Alarcón",      3667,  3600,  2925,  1967, 3350),
    ("Majadahonda",             3800,  3075,  3696,  1885, None),
    ("Boadilla del Monte",      None,  1900,  2480,  3212, 2262),
    ("San Sebastián de los Reyes", 1425, 1002, 2000, None, 2900),
    ("Tres Cantos",             1545,  1314,  1017,  1798, 2600),
    ("Alcalá de Henares",       1120,  1090,  1117,  None, None),
    ("Torrejón de Ardoz",       1193,  1197,  1084,  None,  895),
    ("Rivas-Vaciamadrid",       2090,  None,  1725,  None, 1200),
    ("Coslada",                 1509,  1276,  1910,  1150, 2800),
    ("San Fernando de Henares", 1340,  1292,  1748,  1150, None),
    ("Villanueva de la Cañada", None,  None,  None,  None, 1350),
    ("Villanueva del Pardillo",  3300, None,  None,  None, 1505),
    ("Galapagar",               4200,  1308,  1400,  1373, 1033),
    ("Collado Villalba",        None,  2175,  2038,  1392, 1220),
]


def seed_portals(db):
    existing = {p.key for p in db.query(Portal).all()}
    added = 0
    for p in PORTALS:
        if p["key"] not in existing:
            db.add(Portal(**p))
            added += 1
    db.flush()
    log.info(f"Portals: {added} added, {len(existing)} already present")


def seed_districts(db):
    existing = {d.name for d in db.query(District).all()}
    added = 0
    for name in DISTRICTS_MADRID:
        if name not in existing:
            db.add(District(name=name, city="Madrid", zone="A"))
            added += 1
    # Municipalities that appear as district references in neighborhoods
    muni_names = {n[1] for n in NEIGHBORHOODS if n[2] != "Madrid"}
    for name in muni_names:
        if name not in existing and name not in DISTRICTS_MADRID:
            db.add(District(name=name, city=name, zone=None))
            added += 1
    db.flush()
    log.info(f"Districts: {added} added, {len(existing)} already present")


def seed_neighborhoods(db):
    # Build district lookup by name
    district_map = {d.name: d.id for d in db.query(District).all()}
    existing_keys = {
        (n.municipality, n.name) for n in db.query(Neighborhood).all()
    }
    added = 0
    for row in NEIGHBORHOODS:
        (name, district_name, municipality, safety, transport,
         sol_min, sol_max, atocha_min, atocha_max, zone, notes) = row
        key = (municipality, name)
        if key in existing_keys:
            continue
        district_id = district_map.get(district_name)
        db.add(Neighborhood(
            name=name,
            district_id=district_id,
            municipality=municipality,
            zone=zone,
            safety_score=safety,
            transport_score=transport,
            commute_to_sol_min=sol_min,
            commute_to_sol_max=sol_max,
            commute_to_atocha_min=atocha_min,
            commute_to_atocha_max=atocha_max,
            notes=notes,
        ))
        added += 1
    db.flush()
    log.info(f"Neighborhoods: {added} added")


def seed_cost_benchmarks(db):
    from sqlalchemy.dialects.postgresql import insert as pg_insert
    from mrf.db.models import CostBenchmark
    added = 0
    for scope_name, r1, r2, r3, rh, rc in COST_BENCHMARKS_DISTRICTS:
        exists = (
            db.query(CostBenchmark)
            .filter_by(scope_kind="district", scope_name=scope_name, observed_at=SNAPSHOT_DATE)
            .first()
        )
        if not exists:
            db.add(CostBenchmark(
                scope_kind="district",
                scope_name=scope_name,
                avg_rent_1bed=r1,
                avg_rent_2bed=r2,
                avg_rent_3bed=r3,
                avg_house=rh,
                avg_chalet=rc,
                observed_at=SNAPSHOT_DATE,
                source=SOURCE,
            ))
            added += 1
    for scope_name, r1, r2, r3, rh, rc in COST_BENCHMARKS_MUNICIPALITIES:
        exists = (
            db.query(CostBenchmark)
            .filter_by(scope_kind="municipality", scope_name=scope_name, observed_at=SNAPSHOT_DATE)
            .first()
        )
        if not exists:
            db.add(CostBenchmark(
                scope_kind="municipality",
                scope_name=scope_name,
                avg_rent_1bed=r1,
                avg_rent_2bed=r2,
                avg_rent_3bed=r3,
                avg_house=rh,
                avg_chalet=rc,
                observed_at=SNAPSHOT_DATE,
                source=SOURCE,
            ))
            added += 1
    db.flush()
    log.info(f"Cost benchmarks: {added} added")


def main():
    log.info("Starting seed...")
    with get_db() as db:
        seed_portals(db)
        seed_districts(db)
        seed_neighborhoods(db)
        seed_cost_benchmarks(db)
    log.info("Seed complete.")


if __name__ == "__main__":
    main()
