import os
from dotenv import load_dotenv

import requests
import time
import datetime
import pandas as pd

from snowflake.connector import connect
from snowflake.connector.pandas_tools import write_pandas

load_dotenv()
POLYGON_API_KEY = os.getenv("POLYGON_API_KEY")
SNOWFLAKE_ACCOUNT = os.getenv("SNOWFLAKE_ACCOUNT")
SNOWFLAKE_USER = os.getenv("SNOWFLAKE_USER")
SNOWFLAKE_PASSWORD = os.getenv("SNOWFLAKE_PASSWORD")

LIMIT = 1000

url = f"https://api.polygon.io/v3/reference/tickers?market=stocks&active=true&order=asc&limit={LIMIT}&sort=ticker&apiKey={POLYGON_API_KEY}"

response = requests.get(url)
time.sleep(12)
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
    time.sleep(12)
    data = response.json()

df = pd.DataFrame(list_of_results)
df["ingested_at"] = datetime.datetime.now(datetime.UTC)

conn = connect(
    account=SNOWFLAKE_ACCOUNT,
    user=SNOWFLAKE_USER,
    password=SNOWFLAKE_PASSWORD,
    database="STOCK_TRADING_APP",
    schema="PUBLIC"
)

success, nchunks, nrows, _ = write_pandas(
    conn, df, "tickers", auto_create_table=True, use_logical_type=True 
)