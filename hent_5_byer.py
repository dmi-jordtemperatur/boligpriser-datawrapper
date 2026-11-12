import csv
import time
from datetime import date
from pathlib import Path

import requests

API_URL = "https://api.boligsiden.dk/cases/stats"
BYER = ["København", "Aarhus", "Odense", "Aalborg", "Esbjerg"]
BOLIGTYPER = {
    "villa and terraced house": "villa_raekkehus",
    "condo": "ejerlejlighed",
    "holiday house": "fritidsbolig",
}

# En tidsserie pr. kombination af kommune og boligtype.
serier = {
    filnavn: {by: {} for by in BYER}
    for filnavn in BOLIGTYPER.values()
}

session = requests.Session()

for by in BYER:
    payload = [
        {
            "addressType": api_type,
            "from": "2011-01-01",
            "to": date.today().isoformat(),
            "locationName": by,
            "locationType": "municipality",
            "type": "sold_per_area_price",
        }
        for api_type in BOLIGTYPER
    ]

    svar = session.post(
        API_URL,
        json=payload,
        headers={
            "Accept": "application/json",
            "Origin": "https://www.boligsiden.dk",
            "Referer": "https://www.boligsiden.dk/",
        },
        timeout=90,
    )
    svar.raise_for_status()
    data = svar.json()

    if not isinstance(data, list) or len(data) != len(BOLIGTYPER):
        raise ValueError(f"Uventet antal API-svar for {by}")

    for (api_type, filnavn), poster in zip(BOLIGTYPER.items(), data):
        if poster is None:
            print(f"Ingen data: {by} / {filnavn}", flush=True)
            continue
        if not isinstance(poster, list):
            raise ValueError(f"Uventet datastruktur for {by} / {filnavn}")

        for post in poster:
            if not isinstance(post, dict):
                raise ValueError(f"Ugyldig datapost for {by} / {filnavn}")
            if (
                post.get("addressType") != api_type
                or post.get("locationName") != by
                or post.get("locationType") != "municipality"
                or post.get("type") != "sold_per_area_price"
            ):
                raise ValueError(f"Forkert dataserie for {by} / {filnavn}")

            maaned = post.get("from")
            pris = post.get("value")
            if not isinstance(maaned, str) or len(maaned) != 10:
                raise ValueError(f"Ugyldig dato for {by} / {filnavn}")
            if isinstance(pris, bool) or not isinstance(pris, (int, float)):
                continue
            if pris <= 0:
                raise ValueError(f"Ugyldig pris for {by} / {filnavn}")

            tidligere = serier[filnavn][by].get(maaned)
            if tidligere is not None and tidligere != pris:
                raise ValueError(f"Uens værdier for {by} / {filnavn} / {maaned}")
            serier[filnavn][by][maaned] = pris

    print(f"Behandlet: {by}", flush=True)
    time.sleep(1)

# Afbryd uden at overskrive filer, hvis der slet ingen data er for en boligtype.
for filnavn, bydata in serier.items():
    if not any(bydata[by] for by in BYER):
        raise ValueError(f"Ingen prisdata for boligtypen {filnavn}")

Path("data").mkdir(exist_ok=True)

for filnavn, bydata in serier.items():
    maaneder = sorted({maaned for priser in bydata.values() for maaned in priser})
    sti = Path("data") / f"5_byer_{filnavn}.csv"
    with sti.open("w", encoding="utf-8", newline="") as fil:
        writer = csv.writer(fil)
        writer.writerow(["Dato", *BYER])
        for maaned in maaneder:
            writer.writerow([maaned, *(bydata[by].get(maaned, "") for by in BYER)])

    antal_byer = sum(bool(priser) for priser in bydata.values())
    print(f"{sti}: {len(maaneder)} måneder, {antal_byer} kommuner med data", flush=True)
