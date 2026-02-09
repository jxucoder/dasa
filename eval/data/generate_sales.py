"""Generate sales.csv for DASA evaluation."""
import csv
import random
from datetime import datetime, timedelta

random.seed(42)

start_date = datetime(2023, 1, 1)
end_date = datetime(2024, 12, 31)
date_range_days = (end_date - start_date).days

regions = ["North", "South", "East", "West"]
categories = ["A", "B", "C", "D", "E"]
first_names = [
    "alice", "bob", "carol", "dave", "eve", "frank", "grace", "heidi",
    "ivan", "judy", "karl", "laura", "mike", "nancy", "oscar", "pat",
    "quinn", "rose", "steve", "tina", "uma", "vic", "wendy", "xena",
    "yuri", "zara",
]
domains = ["example.com", "test.org", "company.net", "mail.co", "biz.io"]

rows = []
for i in range(1, 1001):
    date = start_date + timedelta(days=random.randint(0, date_range_days))
    region = random.choice(regions)
    category = random.choice(categories)

    # Revenue: 5% nulls, 2% negative among non-null
    r = random.random()
    if r < 0.05:
        revenue = ""
    elif r < 0.07:
        revenue = round(-random.uniform(10, 500), 2)
    else:
        revenue = round(random.uniform(100, 50000), 2)

    cost = round(random.uniform(50, 20000), 2)

    # Email: 3% nulls
    if random.random() < 0.03:
        email = ""
    else:
        name = random.choice(first_names)
        domain = random.choice(domains)
        email = f"{name}{random.randint(1, 999)}@{domain}"

    rows.append([i, date.strftime("%Y-%m-%d"), region, revenue, cost, category, email])

with open("/home/user/dasa/eval/data/sales.csv", "w", newline="") as f:
    writer = csv.writer(f)
    writer.writerow(["id", "date", "region", "revenue", "cost", "category", "email"])
    writer.writerows(rows)

print(f"Generated {len(rows)} rows")
