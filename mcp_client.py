from contextlib import AsyncExitStack

import httpx
from loguru import logger
from mcp import ClientSession
from mcp.client.streamable_http import streamable_http_client
from langchain_mcp_adapters.tools import load_mcp_tools

from app.tools.handoff_tool import transfer_to_triage_agent_tool
from app.agents.hotel_agent import build_hotel_agent


async def connect_hotel_agent(user_id: str, exit_stack: AsyncExitStack):
    server_url = f"http://localhost:8001/mcp"
    http_client = await exit_stack.enter_async_context(
        httpx.AsyncClient(headers={"X-User-ID": user_id})
    )

    read, write, _ = await exit_stack.enter_async_context(
        streamable_http_client(server_url, http_client=http_client)
    )

    session = await exit_stack.enter_async_context(ClientSession(read, write))
    await session.initialize()

    tools = await load_mcp_tools(session)
    logger.info(
        f"[mcp] user_id={user_id} loaded tools: {[tool.name for tool in tools]}"
    )

    return build_hotel_agent(tools + [transfer_to_triage_agent_tool])
