"""Download, clean, and export source transactions to SQLite for SQL exploration."""
from pathlib import Path
import sqlite3
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from src.data import load_transactions  # noqa: E402


def main() -> None:
    sales, audit = load_transactions()
    destination = ROOT / "data" / "processed" / "retail.sqlite"
    destination.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(destination) as connection:
        sales.to_sql("transactions", connection, if_exists="replace", index=False, chunksize=10000)
        connection.execute("CREATE INDEX IF NOT EXISTS idx_invoice_date ON transactions(invoice_date)")
        connection.execute("CREATE INDEX IF NOT EXISTS idx_customer_id ON transactions(customer_id)")
    print(f"Exported {len(sales):,} sales lines to {destination}")
    print(f"Data-quality audit: {audit}")


if __name__ == "__main__":
    main()
