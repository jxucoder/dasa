"""Generate sample sales data for the DASA example workspace."""
import csv
import random
from datetime import datetime, timedelta

random.seed(42)

start_date = datetime(2024, 1, 1)
end_date = datetime(2024, 12, 31)
date_range_days = (end_date - start_date).days

regions = ["North", "South", "East", "West"]
categories = ["Electronics", "Clothing", "Food", "Home", "Sports"]

rows = []
for i in range(1, 501):
    date = start_date + timedelta(days=random.randint(0, date_range_days))
    region = random.choice(regions)
    category = random.choice(categories)

    # Revenue: 5% nulls, 2% negative (data quality issues for demo)
    r = random.random()
    if r < 0.05:
        revenue = ""
    elif r < 0.07:
        revenue = round(-random.uniform(10, 500), 2)
    else:
        revenue = round(random.uniform(50, 10000), 2)

    cost = round(random.uniform(20, 5000), 2)

    # Units: 3% nulls
    if random.random() < 0.03:
        units = ""
    else:
        units = random.randint(1, 200)

    rows.append([i, date.strftime("%Y-%m-%d"), region, category, revenue, cost, units])

with open("sales.csv", "w", newline="") as f:
    writer = csv.writer(f)
    writer.writerow(["id", "date", "region", "category", "revenue", "cost", "units"])
    writer.writerows(rows)

print(f"Generated {len(rows)} rows -> sales.csv")
