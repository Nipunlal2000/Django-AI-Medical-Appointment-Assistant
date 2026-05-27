# mcp_server.py
from fastmcp import FastMCP
import httpx

mcp = FastMCP("Django Sidecar Server")

@mcp.tool()
async def query_django_users() -> str:
    """Queries the main Django application database to grab user metrics."""
    async with httpx.AsyncClient() as client:
        try:
            # Connects directly to your WSGI server running on port 8000
            response = await client.get("http://127.0.0.1:8000/api/internal/user-count/")
            if response.status_code == 200:
                data = response.json()
                return f"Total users registered in DB: {data.get('count', 0)}"
            return "Could not retrieve user count from primary backend."
        except Exception as e:
            return f"Internal connection failure: {str(e)}"

if __name__ == "__main__":
    mcp.run(transport="sse", port=8080)