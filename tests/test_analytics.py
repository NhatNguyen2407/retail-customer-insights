"""Use synthetic transactions to test calculations without network access."""
import pandas as pd
import pytest

from src.analytics import key_metrics, monthly_revenue, rfm_customers, segment_summary, top_products
from src.data import clean_transactions


def raw_rows():
    return pd.DataFrame([
        ["1001", "A", "Toy A", 2, "2011-01-01 09:00", 10, 1, "UK"],
        ["1001", "B", "Toy B", 1, "2011-01-01 09:00", 20, 1, "UK"],
        ["1002", "A", "Toy A", 3, "2011-02-02 10:00", 10, 1, "UK"],
        ["1003", "C", "Toy C", 1, "2011-02-03 12:00", 5, 2, "FR"],
        ["1004", "C", "Toy C", 1, "2011-02-05 12:00", 7, None, "FR"],
        ["C1005", "A", "Toy A", -1, "2011-02-06 10:00", 10, 1, "UK"],
        ["1006", "A", "Toy A", -2, "2011-02-07 11:00", 10, 1, "UK"],
        ["1007", "A", "Toy A", 1, "bad", 10, 1, "UK"],
        ["1008", "A", "Toy A", 1, "2011-02-08 11:00", 0, 1, "UK"],
    ], columns=["InvoiceNo", "StockCode", "Description", "Quantity",
                "InvoiceDate", "UnitPrice", "CustomerID", "Country"])


def test_cleaning_and_audit():
    sales, audit = clean_transactions(raw_rows())
    assert len(sales) == 5
    assert audit == {
        "source_rows": 9, "cancelled_rows": 1,
        "invalid_sale_rows": 3, "valid_rows": 5, "anonymous_rows": 1,
    }
    assert (sales["revenue"] > 0).all()
    assert sales["invoice_no"].nunique() == 4


def test_kpis_distinct_invoices_and_missing_customer():
    sales, _ = clean_transactions(raw_rows())
    assert key_metrics(sales) == {"revenue": 82.0, "orders": 4, "aov": 20.5, "customers": 2}


def test_rfm_reference_and_uniqueness():
    sales, _ = clean_transactions(raw_rows())
    rfm = rfm_customers(sales)
    assert len(rfm) == 2
    assert set(rfm["customer_id"]) == {"1", "2"}
    c1 = rfm.set_index("customer_id").loc["1"]
    assert c1["frequency"] == 2
    assert c1["monetary"] == 70
    assert c1["recency"] == 2  # 2011-02-04 minus 2011-02-02
    assert rfm[["r_score", "f_score", "m_score"]].min().min() >= 1
    assert rfm[["r_score", "f_score", "m_score"]].max().max() <= 5
    assert segment_summary(rfm)["revenue"].sum() == pytest.approx(75)


def test_monthly_revenue_and_products():
    sales, _ = clean_transactions(raw_rows())
    months = monthly_revenue(sales)
    assert months["revenue"].tolist() == [40.0, 42.0]
    assert top_products(sales, 1).iloc[0]["stock_code"] == "A"


def test_empty_and_schema_validation():
    with pytest.raises(ValueError, match="Missing columns"):
        clean_transactions(pd.DataFrame({"irrelevant": [1]}))
    sales, _ = clean_transactions(raw_rows())
    assert key_metrics(sales.iloc[0:0])["aov"] == 0
    assert rfm_customers(sales[sales["customer_id"].isna()]).empty
