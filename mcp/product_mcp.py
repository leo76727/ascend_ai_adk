import os
import sqlite3
from typing import TypedDict, Optional

from pydantic import BaseModel, Field

try:
    from config import config
    DB_PATH = config.DB_PATH
except Exception:
    DB_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "data", "positions.db"))

try:
    from mcp.server.fastmcp import FastMCP
except Exception:
    FastMCP = None  # type: ignore

try:
    from sqlalchemy import create_engine, text
except Exception:
    create_engine = None  # type: ignore
    text = None  # type: ignore


class ProductModel(BaseModel):
    product_id: str = Field(..., max_length=20)
    isin: str = Field(..., max_length=12)  # UNIQUE NOT NULL
    underlyer_id: Optional[str] = Field(None, max_length=20)  # NULL for basket type
    underlyer_type: str = Field(..., max_length=10)  # CHECK (underlyer_type IN ('stock', 'basket'))
    basket_id: Optional[str] = Field(None, max_length=20)  # NULL for stock type
    issue_date: str = Field(...)  # DATE NOT NULL
    expiration_date: str = Field(...)  # DATE NOT NULL
    payoff_type: str = Field(...)  # CHECK (payoff_type IN ('autocall', 'reverse_convertible', 'capital_guaranteed', 'accumulator'))
    knock_in_level: Optional[float] = Field(None, description="DECIMAL(8,4)")
    knock_out_level: Optional[float] = Field(None, description="DECIMAL(8,4)")
    principal_protected: bool = Field(...)


class ProductsResponse(BaseModel):
    count: int
    products: list[ProductModel]


class ProductInfo(TypedDict):
    product_id: str
    product_description: str


class ProductStore:
    def __init__(self, db_path: str = DB_PATH):
        self.db_path = db_path

    def _connect(self):
        if isinstance(self.db_path, str) and (self.db_path.startswith("postgres") or "://" in self.db_path and not self.db_path.endswith(".db")) and create_engine is not None:
            engine = create_engine(self.db_path)
            return engine.connect()
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def list_products(self, limit: int = 100, offset: int = 0) -> list[dict]:
        sql = "SELECT * FROM product ORDER BY product_id LIMIT :limit OFFSET :offset"
        conn = self._connect()
        try:
            if hasattr(conn, "execute") and text is not None:
                result = conn.execute(text(sql), {"limit": limit, "offset": offset})
                rows = [dict(r) for r in result.mappings().all()]
                conn.close()
                return rows
        except Exception:
            pass
        cur = conn.cursor()
        cur.execute(sql.replace(":limit", "?").replace(":offset", "?"), (limit, offset))
        rows = cur.fetchall()
        conn.close()
        return [dict(r) for r in rows]

    def get_product(self, product_id: str) -> Optional[dict]:
        sql = "SELECT * FROM product WHERE product_id = :product_id"
        conn = self._connect()
        try:
            if hasattr(conn, "execute") and text is not None:
                result = conn.execute(text(sql), {"product_id": product_id})
                row = result.mappings().first()
                conn.close()
                return dict(row) if row else None
        except Exception:
            pass
        cur = conn.cursor()
        cur.execute("SELECT * FROM product WHERE product_id = ?", (product_id,))
        row = cur.fetchone()
        conn.close()
        return dict(row) if row else None


store = ProductStore()
mcp = FastMCP("Product MCP") if FastMCP is not None else None


def _to_product_model(row: dict) -> ProductModel:
    return ProductModel(
        product_id=row.get("product_id"),
        product_description=row.get("product_description"),
        payoff_type=row.get("payoff_type"),
        issue_date=row.get("issue_date"),
        expiration_date=row.get("expiration_date"),
        issuer=row.get("issuer"),
        underlyer_stocks=row.get("underlyer_stocks"),
        co_issuers=row.get("co_issuers"),
        issue_price=row.get("issue_price"),
        issue_size=row.get("issue_size"),
        strike=row.get("strike"),
        coupon=row.get("coupon"),
        barrier_type=row.get("barrier_type"),
        currency=row.get("currency"),
        notional=row.get("notional"),
    )


if mcp is not None:
    @mcp.tool()
    def list_products(limit: int = 100, offset: int = 0) -> ProductsResponse:
        rows = store.list_products(limit=limit, offset=offset)
        models = [_to_product_model(r) for r in rows]
        return ProductsResponse(count=len(models), products=models)


    @mcp.tool()
    def get_product(product_id: str) -> Optional[ProductModel]:
        row = store.get_product(product_id)
        return _to_product_model(row) if row else None


    @mcp.tool()
    def get_product_info(product_id: str) -> Optional[ProductInfo]:
        row = store.get_product(product_id)
        if not row:
            return None
        return ProductInfo(product_id=row["product_id"], product_description=row.get("product_description"))  # type: ignore[arg-type]

else:
    def list_products(limit: int = 100, offset: int = 0) -> ProductsResponse:
        rows = store.list_products(limit=limit, offset=offset)
        models = [_to_product_model(r) for r in rows]
        return ProductsResponse(count=len(models), products=models)


    def get_product(product_id: str) -> Optional[ProductModel]:
        row = store.get_product(product_id)
        return _to_product_model(row) if row else None


    def get_product_info(product_id: str) -> Optional[ProductInfo]:
        row = store.get_product(product_id)
        if not row:
            return None
        return ProductInfo(product_id=row["product_id"], product_description=row.get("product_description"))  # type: ignore[arg-type]


__all__ = ["mcp", "store", "list_products", "get_product", "get_product_info"]

def main():
    """Entry point for the direct execution server."""
    mcp.run()


if __name__ == "__main__":
    main()