from mcp.server.fastmcp import FastMCP
from . import tools

mcp = FastMCP("postgres-mcp")

# Register tools
mcp.add_tool(tools.query_db)
mcp.add_tool(tools.execute_db)
mcp.add_tool(tools.get_article_by_link)
mcp.add_tool(tools.get_latest_articles)

if __name__ == "__main__":
    mcp.run()
