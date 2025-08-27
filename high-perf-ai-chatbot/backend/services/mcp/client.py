import asyncio
import os
from dotenv import load_dotenv

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

from langchain_mcp_adapters.tools import load_mcp_tools
from langgraph.prebuilt import create_react_agent
from langchain_google_genai import ChatGoogleGenerativeAI

load_dotenv()
google_api_key = os.getenv("GOOGLE_API_KEY")

async def run_mcp_client():
    # Start your MCP server (services/mcp/server.py)
    server_params = StdioServerParameters(
        command="python",
        args=[os.path.abspath("services/mcp/server.py")],
    )

    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()

            # Load MCP tools (query_db, execute_db, etc.)
            tools = await load_mcp_tools(session)

            # Gemini as the reasoning LLM
            llm = ChatGoogleGenerativeAI(
                model="gemini-2.5-pro",
                google_api_key=google_api_key,
            )

            # Create an agent with Gemini + MCP tools
            agent = create_react_agent(llm, tools)

            # Example query
            query = "Get me the latest articles about sustainability"
            response = await agent.ainvoke({"messages": query})
            print("Agent response:", response)

if __name__ == "__main__":
    asyncio.run(run_mcp_client())
