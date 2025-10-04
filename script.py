import os
from dotenv import load_dotenv

import requests
import polars as pl

load_dotenv()
POLYGON_API_KEY = os.getenv("POLYGON_API_KEY")

LIMIT = 1000

url = f"https://api.polygon.io/v3/reference/tickers?market=stocks&active=true&order=asc&limit={LIMIT}&sort=ticker&apiKey={POLYGON_API_KEY}"

response = requests.get(url)
data = response.json()

list_of_results = []

while True:
    if not data.get("results"):
        break
    list_of_results.extend(data["results"])
    if not data.get("next_url"):
        break
    next_url = f"{data['next_url']}&apiKey={POLYGON_API_KEY}"
    response = requests.get(next_url)
    data = response.json()

df = pl.DataFrame(list_of_results)