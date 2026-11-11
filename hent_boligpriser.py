
import csv
from datetime import date
from pathlib import Path

import requests

URL = "https://api.boligsiden.dk/cases/stats"

payload = [{
    "addressType": "villa and terraced house",
    "from": "2011-01-01",
    "locationName": "København",
    "locationType": "municipality",
    "to": date.today().isoformat(),
    "type": "sold_per_area_price"
}]

response = requests.post(
    URL,
    json=payload,
    headers={
        "Accept": "application/json",
        "Origin": "https://www.boligsiden.dk",
        "Referer": "https://www.boligsiden.dk/"
    },
    timeout=30
)

response.raise_for_status()
data = response.json()

if not isinstance(data, list) or len(data) != 1:
    raise ValueError("Uventet svar fra Boligsiden")

records = data[0]

if not isinstance(records, list) or not records:
    raise ValueError("Ingen prisdata modtaget")

rows = []

for record in records:
    if record.get("type") != "sold_per_area_price":
        continue

    value = record.get("value")
    month = record.get("from")

    if value is not None and month:
        rows.append((month, value))

if not rows:
    raise ValueError("Ingen gyldige kvadratmeterpriser")

rows.sort()

Path("data").mkdir(exist_ok=True)

with open(
    "data/koebenhavn_villa.csv",
    "w",
    newline="",
    encoding="utf-8"
) as file:
    writer = csv.writer(file)
    writer.writerow(["Dato", "København"])
    writer.writerows(rows)

print(f"Gemt {len(rows)} månedlige priser")
