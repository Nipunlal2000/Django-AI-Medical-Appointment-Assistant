# mcp_server.py
from fastmcp import FastMCP
import httpx
import asyncpg
import json

mcp = FastMCP("Django + Postgres Sidecar Server")

# PostgreSQL Connection Credentials from your .env
DB_CONFIG = {
    "user": "postgres",
    "password": "7204",
    "database": "test_db",
    "host": "localhost",
    "port": 5432
}

@mcp.tool()
async def execute_readonly_query(sql_query: str) -> str:
    """
    Executes a raw read-only SQL query against the test_db PostgreSQL database 
    and returns the rows formatted as a JSON string.
    """
    # Force basic protection against write operations if desired
    upper_query = sql_query.upper()
    if any(keyword in upper_query for keyword in ["DROP", "DELETE", "UPDATE", "INSERT", "ALTER"]):
        return "Error: Only read-only SELECT queries are permitted via this tool."

    try:
        # Establish a fast async connection
        conn = await asyncpg.connect(**DB_CONFIG)
        try:
            # Fetch data records
            rows = await conn.fetch(sql_query)
            # Convert record rows into standard serializable dictionaries
            result_data = [dict(row) for row in rows]
            return json.dumps(result_data, default=str, indent=2)
        finally:
            await conn.close()
    except Exception as e:
        return f"Database execution error: {str(e)}"

# Keep your old Django API tracking tool alive too!
@mcp.tool()
async def query_django_users() -> str:
    """Queries the main Django application database to grab user metrics."""
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get("http://127.0.0.1:8000/api/internal/user-count/")
            if response.status_code == 200:
                return f"Total users registered in DB: {response.json().get('count', 0)}"
            return "Could not retrieve user count."
        except Exception as e:
            return f"Internal connection failure: {str(e)}"

if __name__ == "__main__":
    mcp.run(transport="sse", port=8080)