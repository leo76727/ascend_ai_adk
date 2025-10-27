import os
import sqlite3
from typing import TypedDict, Optional
from pydantic import BaseModel, Field
from mcp.server.fastmcp import FastMCP

DB_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "data", "positions.db"))

class ClientModel(BaseModel):
    client_id: str
    client_name: Optional[str] = None
    client_account: Optional[str] = None
    client_address: Optional[str] = None


class ClientsResponse(BaseModel):
    count: int
    clients: list[ClientModel]


class ClientInfo(TypedDict):
    client_id: str
    client_name: str

class ClientStore:
    def __init__(self, db_path: str = DB_PATH):
        self.db_path = db_path

    def _connect(self):
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def list_clients(self, limit: int = 100, offset: int = 0) -> list[dict]:
        sql = "SELECT client_id, client_name, client_account, client_address FROM clients ORDER BY client_id LIMIT ? OFFSET ?"
        conn = self._connect()
        cur = conn.cursor()
        cur.execute(sql, (limit, offset))
        rows = cur.fetchall()
        conn.close()
        return [dict(r) for r in rows]

    def get_client(self, client_id: str) -> Optional[dict]:
        conn = self._connect()
        cur = conn.cursor()
        cur.execute("SELECT * FROM clients WHERE client_id = ?", (client_id,))
        row = cur.fetchone()
        conn.close()
        return dict(row) if row else None

# Create multiple MCP servers
store = ClientStore()
client_mcp_server = FastMCP("Clients MCP", stateless_http=True)

def _to_client_model(row: dict) -> ClientModel:
    return ClientModel(
        client_id=row.get("client_id"),
        client_name=row.get("client_name"),
        client_account=row.get("client_account"),
        client_address=row.get("client_address"),
    )

@client_mcp_server.tool()
def list_clients(limit: int = 100, offset: int = 0) -> ClientsResponse:
        """List clients with pagination."""
        rows = store.list_clients(limit=limit, offset=offset)
        models = [_to_client_model(r) for r in rows]
        return ClientsResponse(count=len(models), clients=models)


@client_mcp_server.tool()
def get_client(client_id: str) -> Optional[ClientModel]:
    """Get a client by client_id."""
    row = store.get_client(client_id)
    return _to_client_model(row) if row else None


@client_mcp_server.tool()
def get_client_info(client_id: str) -> Optional[ClientInfo]:
    """Get basic client info by client_id."""
    row = store.get_client(client_id)
    if not row:
        return None
    return ClientInfo(client_id=row["client_id"], client_name=row.get("client_name"))  # type: ignore[arg-type]

__all__ = ["client_mcp_server", "store", "list_clients", "get_client", "get_client_info"]
def main():
    """Entry point for the direct execution server."""
    client_mcp_server.run()


if __name__ == "__main__":
    main()