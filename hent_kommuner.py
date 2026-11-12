
import csv
import time
from datetime import date
from pathlib import Path

import requests

URL = "https://api.boligsiden.dk/cases/stats"

KOMMUNER = [
    "Albertslund", "Allerød", "Assens", "Ballerup",
    "Billund", "Bornholm", "Brøndby", "Brønderslev",
    "Dragør", "Egedal", "Esbjerg", "Fanø",
    "Favrskov", "Faxe", "Fredensborg", "Fredericia",
    "Frederiksberg", "Frederikshavn", "Frederikssund",
    "Furesø", "Faaborg-Midtfyn", "Gentofte",
    "Gladsaxe", "Glostrup", "Greve", "Gribskov",
    "Guldborgsund", "Haderslev", "Halsnæs", "Hedensted",
    "Helsingør", "Herlev", "Herning", "Hillerød",
    "Hjørring", "Holbæk", "Holstebro", "Horsens",
    "Hvidovre", "Høje-Taastrup", "Hørsholm", "Ikast-Brande",
    "Ishøj", "Jammerbugt", "Kalundborg", "Kerteminde",
    "Kolding", "København", "Køge", "Langeland",
    "Lejre", "Lemvig", "Lolland", "Lyngby-Taarbæk",
    "Læsø", "Mariagerfjord", "Middelfart", "Morsø",
    "Norddjurs", "Nordfyns", "Nyborg", "Næstved",
    "Odder", "Odense", "Odsherred", "Randers",
    "Rebild", "Ringkøbing-Skjern", "Ringsted",
    "Roskilde", "Rudersdal", "Rødovre", "Samsø",
    "Silkeborg", "Skanderborg", "Skive", "Slagelse",
    "Solrød", "Sorø", "Stevns", "Struer",
    "Svendborg", "Syddjurs", "Sønderborg", "Thisted",
    "Tønder", "Tårnby", "Vallensbæk", "Varde",
    "Vejen", "Vejle", "Vesthimmerlands", "Viborg",
    "Vordingborg", "Ærø", "Aabenraa", "Aalborg",
    "Aarhus"
]

BOLIGTYPER = {
    "villa and terraced house": "Villa/rækkehus",
    "condo": "Ejerlejlighed",
    "holiday house": "Fritidsbolig",
}

session = requests.Session()

rows = []
fejl = []

for kommune in KOMMUNER:
    payload = [
        {
            "addressType": api_type,
            "from": "2025-01-01",
            "to": date.today().isoformat(),
            "locationName": kommune,
            "locationType": "municipality",
            "type": "sold_per_area_price",
        }
        for api_type in BOLIGTYPER
    ]

    try:
        response = session.post(
            URL,
            json=payload,
            headers={
                "Accept": "application/json",
                "Origin": "https://www.boligsiden.dk",
                "Referer": "https://www.boligsiden.dk/",
            },
            timeout=60,
        )
        response.raise_for_status()
        data = response.json()

        if not isinstance(data, list) or len(data) != 3:
            raise ValueError("Uventet API-svar")

        for api_type, records in zip(BOLIGTYPER, data):
            pris = ""
            maaned = ""
            udvikling = ""

            if not isinstance(records, list):
                raise ValueError("Uventet datastruktur")

            gyldige = [
                r for r in records
                if r.get("type") == "sold_per_area_price"
                and isinstance(r.get("value"), (int, float))
            ]

            if gyldige:
                seneste = max(gyldige, key=lambda r: r["from"])
                pris = seneste["value"]
                maaned = seneste["from"][:7]

                forrige_aar = (
                    seneste.get("previousYear") or {}
                ).get("value")

                if (
                    isinstance(forrige_aar, (int, float))
                    and forrige_aar > 0
                ):
                    udvikling = round(
                        (pris / forrige_aar - 1) * 100, 1
                    )

            rows.append([
                kommune,
                BOLIGTYPER[api_type],
                maaned,
                pris,
                udvikling,
            ])

        print(f"Behandlet: {kommune}", flush=True)

    except (requests.RequestException, ValueError) as exc:
        fejl.append(f"{kommune}: {exc}")
        print(f"FEJL: {kommune}: {exc}", flush=True)

    time.sleep(1)

if fejl:
    raise RuntimeError(
        "Datahentning fejlede for kommuner:\n"
        + "\n".join(fejl)
    )

if len(rows) != len(KOMMUNER) * len(BOLIGTYPER):
    raise RuntimeError("Der mangler rækker i resultatet")

Path("data").mkdir(exist_ok=True)

with open(
    "data/boligpriser_kommuner.csv",
    "w",
    newline="",
    encoding="utf-8",
) as file:
    writer = csv.writer(file)
    writer.writerow([
        "Kommune",
        "Boligtype",
        "Måned",
        "Kr. pr. m²",
        "Årlig udvikling (%)",
    ])
    writer.writerows(rows)

print(f"Færdig: {len(rows)} rækker")
print(
    "Rækker uden pris:",
    sum(1 for row in rows if row[3] == "")
)
