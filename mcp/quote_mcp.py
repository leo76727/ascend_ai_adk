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


class QuoteModel(BaseModel):
    quote_id: str = Field(..., max_length=20)  # PRIMARY KEY
    underlyer_id: str = Field(..., max_length=20)  # NOT NULL, references Underlyer(underlyer_id)
    client_id: str = Field(..., max_length=20)  # NOT NULL, references Client(client_id)
    quantity: float = Field(..., description="DECIMAL(15,2) NOT NULL")
    payoff_type: str = Field(..., max_length=20)  # CHECK (payoff_type IN ('autocall', 'reverse_convertible', 'capital_guaranteed', 'accumulator'))
    price: float = Field(..., description="DECIMAL(10,4) NOT NULL")
    is_traded: bool = Field(default=False)  # NOT NULL DEFAULT FALSE
    quote_date: str = Field(...)  # DATE NOT NULL


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
        if isinstance(self.db_path, str) and (self.db_path.startswith("postgres") or "://" in self.db_path and not self.db_path.endswith(".db")) and create_engine is not None:
            engine = create_engine(self.db_path)
            return engine.connect()
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def list_quotes(self, limit: int = 100, offset: int = 0) -> list[dict]:
        sql = """SELECT quote_id, underlyer_id, client_id, quantity, payoff_type,
                 price, is_traded, quote_date 
                 FROM quote ORDER BY quote_id LIMIT :limit OFFSET :offset"""
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

    def get_quote(self, quote_id: str) -> Optional[dict]:
        sql = "SELECT * FROM quote WHERE quote_id = :quote_id"
        conn = self._connect()
        try:
            if hasattr(conn, "execute") and text is not None:
                result = conn.execute(text(sql), {"quote_id": quote_id})
                row = result.mappings().first()
                conn.close()
                return dict(row) if row else None
        except Exception:
            pass
        cur = conn.cursor()
        cur.execute("SELECT * FROM quote WHERE quote_id = ?", (quote_id,))
        row = cur.fetchone()
        conn.close()
        return dict(row) if row else None


store = QuoteStore()
mcp = FastMCP("Quote MCP") if FastMCP is not None else None


def _to_quote_model(row: dict) -> QuoteModel:
    return QuoteModel(
        quote_id=row["quote_id"],
        underlyer_id=row["underlyer_id"],
        client_id=row["client_id"],
        quantity=float(row["quantity"]),
        payoff_type=row["payoff_type"],
        price=float(row["price"]),
        is_traded=bool(row["is_traded"]),
        quote_date=row["quote_date"]
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
