"""
Example showing how to mount multiple StreamableHTTP servers with path configuration.

Run from the repository root:
    uvicorn ascend_ai_adk.mcp.mcp_server_http:app --reload
"""

from starlette.applications import Starlette
from starlette.routing import Mount
from starlette.middleware.cors import CORSMiddleware
from starlette.routing import Route
from starlette.requests import Request
from starlette.responses import JSONResponse, PlainTextResponse
from typing import Optional
import contextlib

from mcp.server.fastmcp import FastMCP
import uvicorn
import clients_mcp as clients_mcp
import position_mcp as position_mcp
import quote_mcp as quote_mcp
import market_mcp as market_mcp
import product_mcp as product_mcp
import trades_mcp as trades_mcp

client_mcp_server = clients_mcp.client_mcp_server
position_mcp = position_mcp.mcp
quote_mcp = quote_mcp.mcp
market_mcp = market_mcp.mcp
product_mcp = product_mcp.mcp
trades_mcp = trades_mcp.mcp

async def homepage(req: Request):
    return PlainTextResponse("ok: service is running")

# Configure servers to mount at the root of each path
# This means endpoints will be at /api and /chat instead of /api/mcp and /chat/mcp
client_mcp_server.settings.streamable_http_path = "/"
position_mcp.settings.streamable_http_path = "/"
quote_mcp.settings.streamable_http_path = "/"
market_mcp.settings.streamable_http_path = "/"
product_mcp.settings.streamable_http_path = "/"
trades_mcp.settings.streamable_http_path = "/"

@contextlib.asynccontextmanager
async def lifespan(app: Starlette):
    async with contextlib.AsyncExitStack() as stack:
        await stack.enter_async_context(client_mcp_server.session_manager.run())
        await stack.enter_async_context(position_mcp.session_manager.run())
        await stack.enter_async_context(quote_mcp.session_manager.run())
        await stack.enter_async_context(market_mcp.session_manager.run())   
        await stack.enter_async_context(product_mcp.session_manager.run())
        await stack.enter_async_context(trades_mcp.session_manager.run())
        yield

# Mount the servers
app = Starlette(
    routes=[
        Route("/", homepage, methods=["GET"]),
        Mount("/client", app=client_mcp_server.streamable_http_app()),
        Mount("/position", app=position_mcp.streamable_http_app()),
        Mount("/quote", app=quote_mcp.streamable_http_app()),
        Mount("/market", app=market_mcp.streamable_http_app()),
        Mount("/trades", app=trades_mcp.streamable_http_app()),
        Mount("/product", app=product_mcp.streamable_http_app()),
    ],
    lifespan=lifespan
)

starlette_app = CORSMiddleware(
    app,
    allow_origins=["*"],  # Configure appropriately for production
    allow_methods=["GET", "POST", "DELETE"],  # MCP streamable HTTP methods
    expose_headers=["Mcp-Session-Id"],
)

if __name__ == "__main__":
    uvicorn.run(starlette_app, host="0.0.0.0", port=8003) # Host on a different port