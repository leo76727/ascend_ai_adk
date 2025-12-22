import datetime
import os
import sqlite3
from typing import TypedDict, Optional
from mcp.server.fastmcp import FastMCP
from pydantic import BaseModel, Field
from datetime import datetime
from sqlalchemy import create_engine, text
import sys
import os

# Add parent directory to path to allow importing config
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from config import config
DB_PATH = config.DB_PATH

class ProductModel(BaseModel):
    product_id: str = Field(..., max_length=20)
    isin: str = Field(..., max_length=12)  # UNIQUE NOT NULL
    underlyer_id: Optional[str] = Field(None, max_length=20)  # NULL for basket type
    underlyer_type: str = Field(..., max_length=10)  # CHECK (underlyer_type IN ('stock', 'basket'))
    basket_id: Optional[str] = Field(None, max_length=20)  # NULL for stock type
    issue_date: datetime = Field(...)  # DATE NOT NULL
    expiration_date: datetime = Field(...)  # DATE NOT NULL
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
        
        if isinstance(conn, sqlite3.Connection):
            try:
                cur = conn.cursor()
                cur.execute(sql.replace(":limit", "?").replace(":offset", "?"), (limit, offset))
                rows = cur.fetchall()
                conn.close()
                return [dict(r) for r in rows]
            except Exception:
                conn.close()
                return []
        
        # SQLAlchemy path
        try:
            result = conn.execute(text(sql), {"limit": limit, "offset": offset})
            rows = [dict(r) for r in result.mappings().all()]
            conn.close()
            return rows
        except Exception:
            conn.close()
            return []

    def get_product(self, product_id: str) -> Optional[dict]:
        sql = "SELECT * FROM product WHERE product_id = :product_id"
        conn = self._connect()
        
        if isinstance(conn, sqlite3.Connection):
            try:
                cur = conn.cursor()
                cur.execute("SELECT * FROM product WHERE product_id = ?", (product_id,))
                row = cur.fetchone()
                conn.close()
                return dict(row) if row else None
            except Exception:
                conn.close()
                return None

        # SQLAlchemy path
        try:
            result = conn.execute(text(sql), {"product_id": product_id})
            row = result.mappings().first()
            conn.close()
            return dict(row) if row else None
        except Exception:
            conn.close()
            return None


store = ProductStore()
mcp = FastMCP("Product MCP")


def _to_product_model(row: dict) -> ProductModel:
    return ProductModel(
        product_id=row["product_id"],
        isin=row["isin"],
        underlyer_id=row.get("underlyer_id"),
        underlyer_type=row["underlyer_type"],
        basket_id=row.get("basket_id"),
        issue_date=row["issue_date"],
        expiration_date=row["expiration_date"],
        payoff_type=row["payoff_type"],
        knock_in_level=float(row["knock_in_level"]) if row.get("knock_in_level") else None,
        knock_out_level=float(row["knock_out_level"]) if row.get("knock_out_level") else None,
        principal_protected=bool(row["principal_protected"])
    )



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

__all__ = ["mcp", "store", "list_products", "get_product", "get_product_info"]

def main():
    """Entry point for the direct execution server."""
    #mcp.run()
    products=list_products()
    print(products) 


if __name__ == "__main__":
    main()