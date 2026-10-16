"""Load and clean UCI Online Retail transactions."""
from __future__ import annotations

from io import BytesIO
from pathlib import Path
from urllib.request import urlopen
from zipfile import ZipFile

import pandas as pd

SOURCE_URL = "https://archive.ics.uci.edu/static/public/352/online%2Bretail.zip"
DATA_DIR = Path(__file__).resolve().parents[1] / "data"
RAW_FILE = DATA_DIR / "Online Retail.xlsx"
REQUIRED = {
    "InvoiceNo", "StockCode", "Description", "Quantity", "InvoiceDate",
    "UnitPrice", "CustomerID", "Country",
}


def download_data(destination: Path = RAW_FILE) -> Path:
    """Cache the publicly licensed source XLSX file. Does not overwrite existing data."""
    if destination.is_file():
        return destination
    destination.parent.mkdir(parents=True, exist_ok=True)
    with urlopen(SOURCE_URL, timeout=90) as response:
        payload = response.read()
    with ZipFile(BytesIO(payload)) as archive:
        spreadsheets = [name for name in archive.namelist() if name.lower().endswith(".xlsx")]
        if not spreadsheets:
            raise ValueError("UCI archive does not contain an XLSX workbook")
        with archive.open(spreadsheets[0]) as source:
            destination.write_bytes(source.read())
    return destination


def clean_transactions(raw: pd.DataFrame) -> tuple[pd.DataFrame, dict[str, int]]:
    """Keep positive completed sales; report exclusions to make analysis auditable."""
    missing = REQUIRED - set(raw.columns)
    if missing:
        raise ValueError(f"Missing columns: {', '.join(sorted(missing))}")

    df = raw.copy()
    raw_count = len(df)
    df["invoice_no"] = df["InvoiceNo"].astype("string").str.strip()
    df["stock_code"] = df["StockCode"].astype("string").str.strip()
    df["description"] = df["Description"].astype("string").str.strip()
    df["country"] = df["Country"].astype("string").str.strip()
    df["invoice_date"] = pd.to_datetime(df["InvoiceDate"], errors="coerce")
    df["quantity"] = pd.to_numeric(df["Quantity"], errors="coerce")
    df["unit_price"] = pd.to_numeric(df["UnitPrice"], errors="coerce")
    customer = pd.to_numeric(df["CustomerID"], errors="coerce").astype("Int64")
    df["customer_id"] = customer.astype("string")

    cancelled = df["invoice_no"].str.upper().str.startswith("C", na=False)
    invalid_sale = (
        (df["quantity"] <= 0) | (df["unit_price"] <= 0)
        | df["quantity"].isna() | df["unit_price"].isna()
        | df["invoice_date"].isna() | df["invoice_no"].isna()
    )
    keep = ~(cancelled | invalid_sale)
    df = df.loc[keep, [
        "invoice_no", "stock_code", "description", "country",
        "invoice_date", "quantity", "unit_price", "customer_id",
    ]].copy()
    df["revenue"] = df["quantity"] * df["unit_price"]
    df = df.sort_values("invoice_date").reset_index(drop=True)
    quality = {
        "source_rows": raw_count,
        "cancelled_rows": int(cancelled.sum()),
        "invalid_sale_rows": int((invalid_sale & ~cancelled).sum()),
        "valid_rows": len(df),
        "anonymous_rows": int(df["customer_id"].isna().sum()),
    }
    return df, quality


def load_transactions(source: Path | None = None) -> tuple[pd.DataFrame, dict[str, int]]:
    location = source if source is not None else download_data()
    raw = pd.read_excel(location, engine="openpyxl")
    return clean_transactions(raw)
