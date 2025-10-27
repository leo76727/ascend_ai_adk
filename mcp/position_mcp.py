import os
import sqlite3
from typing import TypedDict, Optional

from pydantic import BaseModel, Field

try:
    from mcp.server.fastmcp import FastMCP
except Exception:  # pragma: no cover - FastMCP optional for testing
    FastMCP = None  # type: ignore


DB_PATH = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "data", "positions.db")
)


class PositionModel(BaseModel):
    """Structured representation of a position record."""

    id: int = Field(..., description="Primary key id")
    client_id: str
    product_id: str
    quantity: int
    original_price: float
    expiration_date: str
    current_price: float
    notional: float
    strike: Optional[float] = None
    coupon: Optional[float] = None
    currency: Optional[str] = None


class PositionsResponse(BaseModel):
    count: int
    positions: list[PositionModel]


# A small TypedDict example (also structured but simpler than Pydantic)
class PositionInfo(TypedDict):
    id: int
    client_id: str
    product_id: str
    quantity: int


class PositionStore:
    """SQLite-backed access to the `positions` table."""

    def __init__(self, db_path: str = DB_PATH):
        self.db_path = db_path

    def _connect(self):
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def list_positions(
        self,
        limit: int = 100,
        offset: int = 0,
        client_id: Optional[str] = None,
        product_id: Optional[str] = None,
    ) -> list[dict]:
        q = [
            "SELECT id, client_id, product_id, quantity, original_price, expiration_date,",
            "current_price, notional, strike, coupon, currency FROM positions",
        ]
        params: list = []
        clauses: list[str] = []
        if client_id:
            clauses.append("client_id = ?")
            params.append(client_id)
        if product_id:
            clauses.append("product_id = ?")
            params.append(product_id)
        if clauses:
            q.append("WHERE " + " AND ".join(clauses))
        q.append("ORDER BY id LIMIT ? OFFSET ?")
        params.extend([limit, offset])
        sql = " ".join(q)

        conn = self._connect()
        cur = conn.cursor()
        cur.execute(sql, params)
        rows = cur.fetchall()
        conn.close()
        return [dict(r) for r in rows]

    def get_position(self, position_id: int) -> Optional[dict]:
        conn = self._connect()
        cur = conn.cursor()
        cur.execute("SELECT * FROM positions WHERE id = ?", (position_id,))
        row = cur.fetchone()
        conn.close()
        return dict(row) if row else None


# Create FastMCP instance if available; otherwise expose same callables for
# external registration or local testing.
mcp = FastMCP("Position MCP") if FastMCP is not None else None
store = PositionStore()


def _convert_row_to_position_model(row: dict) -> PositionModel:
    # Convert SQL row dict to Pydantic PositionModel (handles None safely)
    return PositionModel(
        id=int(row["id"]),
        client_id=row.get("client_id"),
        product_id=row.get("product_id"),
        quantity=int(row.get("quantity", 0)),
        original_price=float(row.get("original_price", 0.0)),
        expiration_date=row.get("expiration_date"),
        current_price=float(row.get("current_price", 0.0)),
        notional=float(row.get("notional", 0.0)),
        strike=row.get("strike"),
        coupon=row.get("coupon"),
        currency=row.get("currency"),
    )


if mcp is not None:
    @mcp.tool()
    def list_positions(limit: int = 100, offset: int = 0, client_id: Optional[str] = None, product_id: Optional[str] = None) -> PositionsResponse:
        """Structured: returns PositionsResponse (Pydantic) with list of PositionModel."""
        rows = store.list_positions(limit=limit, offset=offset, client_id=client_id, product_id=product_id)
        models = [_convert_row_to_position_model(r) for r in rows]
        return PositionsResponse(count=len(models), positions=models)


    @mcp.tool()
    def get_position(position_id: int) -> Optional[PositionModel]:
        """Structured: returns a single PositionModel or None."""
        row = store.get_position(position_id)
        return _convert_row_to_position_model(row) if row else None


    @mcp.tool()
    def get_position_info(position_id: int) -> Optional[PositionInfo]:
        """TypedDict: simpler structure useful for lightweight clients."""
        row = store.get_position(position_id)
        if not row:
            return None
        return PositionInfo(id=row["id"], client_id=row["client_id"], product_id=row["product_id"], quantity=row["quantity"])  # type: ignore[call-arg]

    @mcp.tool()
    def list_positions_raw(limit: int = 100) -> dict:
        """Unstructured/dynamic: return raw dicts (flexible schema)."""
        rows = store.list_positions(limit=limit)
        return {"result": rows}


else:  # FastMCP not available; provide local helper functions with same names
    def list_positions(limit: int = 100, offset: int = 0, client_id: Optional[str] = None, product_id: Optional[str] = None) -> PositionsResponse:
        rows = store.list_positions(limit=limit, offset=offset, client_id=client_id, product_id=product_id)
        models = [_convert_row_to_position_model(r) for r in rows]
        return PositionsResponse(count=len(models), positions=models)


    def get_position(position_id: int) -> Optional[PositionModel]:
        row = store.get_position(position_id)
        return _convert_row_to_position_model(row) if row else None


    def get_position_info(position_id: int) -> Optional[PositionInfo]:
        row = store.get_position(position_id)
        if not row:
            return None
        return PositionInfo(id=row["id"], client_id=row["client_id"], product_id=row["product_id"], quantity=row["quantity"])  # type: ignore[call-arg]


__all__ = [
    "mcp",
    "store",
    "list_positions",
    "get_position",
    "get_position_info",
    "list_positions_raw",
]

def main():
    """Entry point for the direct execution server."""
    mcp.run()


if __name__ == "__main__":
    main()