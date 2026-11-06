import sys
from contextlib import asynccontextmanager
from typing import AsyncIterator

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

from ..llm.client import DeepSeekClient
from ..sandbox.executor import SandboxExecutor
from .loop import AgentLoop


@asynccontextmanager
async def mcp_stdio_session() -> AsyncIterator[ClientSession]:
    server_params = StdioServerParameters(
        command=sys.executable,
        args=["-m", "assistant.mcp_server"],
    )
    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            yield session


async def ask_agent(
    user_query: str,
    requester_people_id: str,
    verbose: bool = False,
) -> str:
    async with mcp_stdio_session() as mcp_session:
        agent = AgentLoop(
            llm=DeepSeekClient(),
            sandbox=SandboxExecutor(),
            mcp_session=mcp_session,
            verbose=verbose,
        )
        result = await agent.run(user_query, requester_people_id)
        return result["final_response"]