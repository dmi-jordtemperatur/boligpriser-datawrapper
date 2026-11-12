
import csv
from datetime import date
from pathlib import Path

import requests

URL = "https://api.boligsiden.dk/cases/stats"

# Vi tester først tre kommuner og alle boligtyper.
kommuner = ["København", "Aarhus", "Odense"]

boligtyper = {
    "villa and terraced house": "Villa/rækkehus",
    "condo": "Ejerlejlighed",
    "holiday house": "Fritidsbolig",
}

payload = []

for kommune in kommuner:
    for api_type in boligtyper:
        payload.append({
            "addressType": api_type,
            "from": "2025-01-01",
            "to": date.today().isoformat(),
            "locationName": kommune,
            "locationType": "municipality",
            "type": "sold_per_area_price",
        })

response = requests.post(
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

if not isinstance(data, list) or len(data) != len(payload):
    raise ValueError("Uventet API-svar")

rows = []

for request_item, records in zip(payload, data):
    if not isinstance(records, list) or not records:
        continue

    priser = [
        r for r in records
        if r.get("type") == "sold_per_area_price"
        and isinstance(r.get("value"), (int, float))
    ]

    if not priser:
        continue

    seneste = max(priser, key=lambda r: r["from"])
    forrige_aar = seneste.get("previousYear", {}).get("value")

    udvikling = ""
    if isinstance(forrige_aar, (int, float)) and forrige_aar:
        udvikling = round(
            (seneste["value"] / forrige_aar - 1) * 100, 1
        )

    rows.append([
        request_item["locationName"],
        boligtyper[request_item["addressType"]],
        seneste["from"][:7],
        seneste["value"],
        udvikling,
    ])

if not rows:
    raise ValueError("Ingen boligpriser modtaget")

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

print(f"Gemt {len(rows)} rækker")
