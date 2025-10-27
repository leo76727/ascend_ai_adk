import os
import sqlite3
from typing import TypedDict, Optional

from pydantic import BaseModel

try:
    from mcp.server.fastmcp import FastMCP
except Exception:
    FastMCP = None  # type: ignore


DB_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "data", "positions.db"))


class QuoteModel(BaseModel):
    quote_id: str
    client_id: Optional[str] = None
    payoff_type: Optional[str] = None
    issue_date: Optional[str] = None
    expiration_date: Optional[str] = None
    issuer: Optional[str] = None
    underlyer_stocks: Optional[str] = None
    barrier_level: Optional[float] = None
    gross_credit_level: Optional[float] = None
    barrier_type: Optional[str] = None
    strike: Optional[float] = None
    currency: Optional[str] = None


class QuotesResponse(BaseModel):
    count: int
    quotes: list[QuoteModel]


class QuoteInfo(TypedDict):
    quote_id: str
    client_id: str


class QuoteStore:
    def __init__(self, db_path: str = DB_PATH):
        self.db_path = db_path

    def _connect(self):
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def list_quotes(self, limit: int = 100, offset: int = 0) -> list[dict]:
        sql = "SELECT * FROM quote ORDER BY quote_id LIMIT ? OFFSET ?"
        conn = self._connect()
        cur = conn.cursor()
        cur.execute(sql, (limit, offset))
        rows = cur.fetchall()
        conn.close()
        return [dict(r) for r in rows]

    def get_quote(self, quote_id: str) -> Optional[dict]:
        conn = self._connect()
        cur = conn.cursor()
        cur.execute("SELECT * FROM quote WHERE quote_id = ?", (quote_id,))
        row = cur.fetchone()
        conn.close()
        return dict(row) if row else None


store = QuoteStore()
mcp = FastMCP("Quote MCP") if FastMCP is not None else None


def _to_quote_model(row: dict) -> QuoteModel:
    return QuoteModel(
        quote_id=row.get("quote_id"),
        client_id=row.get("client_id"),
        payoff_type=row.get("payoff_type"),
        issue_date=row.get("issue_date"),
        expiration_date=row.get("expiration_date"),
        issuer=row.get("issuer"),
        underlyer_stocks=row.get("underlyer_stocks"),
        barrier_level=row.get("barrier_level"),
        gross_credit_level=row.get("gross_credit_level"),
        barrier_type=row.get("barrier_type"),
        strike=row.get("strike"),
        currency=row.get("currency"),
    )


if mcp is not None:
    @mcp.tool()
    def list_quotes(limit: int = 100, offset: int = 0) -> QuotesResponse:
        rows = store.list_quotes(limit=limit, offset=offset)
        models = [_to_quote_model(r) for r in rows]
        return QuotesResponse(count=len(models), quotes=models)


    @mcp.tool()
    def get_quote(quote_id: str) -> Optional[QuoteModel]:
        row = store.get_quote(quote_id)
        return _to_quote_model(row) if row else None


    @mcp.tool()
    def get_quote_info(quote_id: str) -> Optional[QuoteInfo]:
        row = store.get_quote(quote_id)
        if not row:
            return None
        return QuoteInfo(quote_id=row["quote_id"], client_id=row.get("client_id"))  # type: ignore[arg-type]

else:
    def list_quotes(limit: int = 100, offset: int = 0) -> QuotesResponse:
        rows = store.list_quotes(limit=limit, offset=offset)
        models = [_to_quote_model(r) for r in rows]
        return QuotesResponse(count=len(models), quotes=models)


    def get_quote(quote_id: str) -> Optional[QuoteModel]:
        row = store.get_quote(quote_id)
        return _to_quote_model(row) if row else None


    def get_quote_info(quote_id: str) -> Optional[QuoteInfo]:
        row = store.get_quote(quote_id)
        if not row:
            return None
        return QuoteInfo(quote_id=row["quote_id"], client_id=row.get("client_id"))  # type: ignore[arg-type]


__all__ = ["mcp", "store", "list_quotes", "get_quote", "get_quote_info"]

def main():
    """Entry point for the direct execution server."""
    mcp.run()


if __name__ == "__main__":
    main()
