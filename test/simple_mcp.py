import uvicorn
from starlette.applications import Starlette
from starlette.routing import Mount, Route
from mcp.server.fastmcp import FastMCP
from starlette.responses import JSONResponse
import contextlib

# (Existing FastMCP server code here)
mcp = FastMCP("MyExampleServer")

@mcp.tool()
def add_numbers(a: int, b: int) -> int:
    """Adds two numbers together."""
    return a + b

# Create the ASGI app for FastMCP on a specific path
mcp_app = mcp.streamable_http_app()

@contextlib.asynccontextmanager
async def lifespan(app: Starlette):
    async with contextlib.AsyncExitStack() as stack:
        await stack.enter_async_context(mcp.session_manager.run())
        yield
# Create the main Starlette application
app = Starlette(
    routes=[
        Mount("/example", app=mcp_app), # Mount the MCP app at "/mcp"
        Route("/", endpoint=lambda req: JSONResponse({"hello": "world"})),
    ],   
    lifespan=lifespan # Important for lifecycle management
)

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)