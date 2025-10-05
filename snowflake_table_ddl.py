import os
from dotenv import load_dotenv

import requests
import pandas as pd
import decimal

from snowflake.connector import connect
from snowflake.connector.pandas_tools import write_pandas

def infer_sf_type(s: pd.Series) -> str:
    dt = s.dtype

    # Datetime → DATE if all times midnight; otherwise TIMESTAMP_NTZ/TZ
    if pd.api.types.is_datetime64_any_dtype(dt):
        tz = getattr(s.dt, "tz", None)
        nonnull = s.dropna()
        if not nonnull.empty and (nonnull.dt.time == pd.Timestamp(0).time()).all():
            return "DATE"
        return "TIMESTAMP_TZ" if tz is not None else "TIMESTAMP_NTZ"

    # Boolean
    if pd.api.types.is_bool_dtype(dt):
        return "BOOLEAN"

    # Integer
    if pd.api.types.is_integer_dtype(dt):
        return "NUMBER(38,0)"

    # Float
    if pd.api.types.is_float_dtype(dt):
        return "FLOAT"

    # String-like and Category
    if pd.api.types.is_string_dtype(dt) or pd.api.types.is_categorical_dtype(dt):
        nonnull = s.dropna().astype(str)
        max_len = int(nonnull.str.len().max()) if not nonnull.empty else 0
        return "VARCHAR" if max_len == 0 else f"VARCHAR({max_len})"

    # Object fallback: detect common shapes
    if pd.api.types.is_object_dtype(dt):
        nonnull = s.dropna()
        if nonnull.empty:
            return "VARCHAR"
        # All bytes-like → BINARY
        if nonnull.map(lambda x: isinstance(x, (bytes, bytearray))).all():
            return "BINARY"
        # Semi-structured (lists/dicts) → VARIANT
        if nonnull.map(lambda x: isinstance(x, (dict, list))).any():
            return "VARIANT"
        # Decimal → NUMBER with rough precision/scale
        if nonnull.map(lambda x: isinstance(x, Decimal)).all():
            def prec_scale(d: Decimal):
                t = d.as_tuple()
                scale = -t.exponent if t.exponent < 0 else 0
                digits = len(t.digits)
                return digits, scale
            ps = [prec_scale(v) for v in nonnull]
            p = max(p for p, _ in ps)
            smax = max(s for _, s in ps)
            p = min(max(p, 1), 38)
            smax = min(max(smax, 0), 37)
            if smax >= p:  # ensure precision > scale
                p = min(smax + 1, 38)
            return f"NUMBER({p},{smax})"
        # Otherwise treat as string
        nonnull_str = nonnull.astype(str)
        max_len = int(nonnull_str.str.len().max()) if not nonnull_str.empty else 0
        return "VARCHAR" if max_len == 0 else f"VARCHAR({max_len})"

    # Fallback
    return "VARCHAR"

def print_snowflake_schema_suggestion(df: pd.DataFrame, table_name: str = "MY_TABLE") -> None:
    if df.empty:
        print("DataFrame is empty; no schema inference available.")
        return
    lines = []
    for col in df.columns:
        s = df[col]
        nullable = s.isna().any()
        sf_type = infer_sf_type(s)
        print(f"{col}: pandas_dtype={s.dtype}, nullable={nullable}, snowflake_type={sf_type}")
        lines.append(f'"{col.upper()}" {sf_type} {"NULL" if nullable else "NOT NULL"}')
    ddl = f'CREATE TABLE {table_name} (\n  ' + ",\n  ".join(lines) + "\n);"
    print("\n-- Suggested DDL --")
    print(ddl)

load_dotenv()
POLYGON_API_KEY = os.getenv("POLYGON_API_KEY")

LIMIT = 1000

url = f"https://api.polygon.io/v3/reference/tickers?market=stocks&active=true&order=asc&limit={LIMIT}&sort=ticker&apiKey={POLYGON_API_KEY}"

response = requests.get(url)
data = response.json()

df = pd.DataFrame(data["results"])

# Print per-column details and suggested CREATE TABLE DDL
print_snowflake_schema_suggestion(df, table_name="TICKERS")