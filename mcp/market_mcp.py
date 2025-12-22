import os
import sqlite3
from typing import TypedDict, Optional
from sqlalchemy import create_engine, text
from pydantic import BaseModel
from mcp.server.fastmcp import FastMCP

try:
    from config import config
    DB_PATH = config.DB_PATH
except Exception:
    DB_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "data", "positions.db"))

class MarketModel(BaseModel):
    product_id: str
    product_description: Optional[str] = None
    payoff_type: Optional[str] = None
    issue_date: Optional[str] = None
    expiration_date: Optional[str] = None
    issuer: Optional[str] = None
    underlyer_stocks: Optional[str] = None
    co_issuers: Optional[str] = None
    issue_price: Optional[float] = None
    issue_size: Optional[int] = None
    strike: Optional[float] = None
    coupon: Optional[float] = None
    barrier_type: Optional[str] = None
    currency: Optional[str] = None
    notional: Optional[float] = None
    estimate_client: Optional[float] = None


class MarketsResponse(BaseModel):
    count: int
    market: list[MarketModel]


class MarketInfo(TypedDict):
    product_id: str
    product_description: str


class MarketStore:
    def __init__(self, db_path: str = DB_PATH):
        self.db_path = db_path

    def _connect(self):
        if isinstance(self.db_path, str) and (self.db_path.startswith("postgres") or "://" in self.db_path and not self.db_path.endswith(".db")) and create_engine is not None:
            engine = create_engine(self.db_path)
            return engine.connect()
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def list_market(self, limit: int = 100, offset: int = 0) -> list[dict]:
        sql = "SELECT * FROM market ORDER BY product_id LIMIT :limit OFFSET :offset"
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

    def get_market(self, product_id: str) -> Optional[dict]:
        sql = "SELECT * FROM market WHERE product_id = :product_id"
        conn = self._connect()
        
        if isinstance(conn, sqlite3.Connection):
            try:
                cur = conn.cursor()
                cur.execute("SELECT * FROM market WHERE product_id = ?", (product_id,))
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


store = MarketStore()
mcp = FastMCP("Market MCP")


def _to_market_model(row: dict) -> MarketModel:
    return MarketModel(
        product_id=row["product_id"],
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
        estimate_client=row.get("estimate_client"),
    )



@mcp.tool()
def list_market(limit: int = 100, offset: int = 0) -> MarketsResponse:
    rows = store.list_market(limit=limit, offset=offset)
    models = [_to_market_model(r) for r in rows]
    return MarketsResponse(count=len(models), market=models)


@mcp.tool()
def get_market(product_id: str) -> Optional[MarketModel]:
    row = store.get_market(product_id)
    return _to_market_model(row) if row else None


@mcp.tool()
def get_market_info(product_id: str) -> Optional[MarketInfo]:
    row = store.get_market(product_id)
    if not row:
        return None
    return MarketInfo(product_id=row["product_id"], product_description=row.get("product_description"))  # type: ignore[arg-type]

__all__ = ["mcp", "store", "list_market", "get_market", "get_market_info" ]

def main():
    """Entry point for the direct execution server."""
    mcp.run()


if __name__ == "__main__":
    main()
