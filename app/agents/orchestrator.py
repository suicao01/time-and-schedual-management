import asyncio

from contextlib import AsyncExitStack

from langchain_docker_backend import DockerSandbox

from loguru import logger
import asyncio
from langchain_core.tools import tool
import uuid
import os

from langchain.agents import create_agent
from dotenv import load_dotenv

from langgraph.checkpoint.memory import InMemorySaver

from langgraph.types import Send, interrupt, Command

from langchain_openai import AzureChatOpenAI
from langchain_core.messages import AIMessage, HumanMessage, RemoveMessage, SystemMessage, ToolMessage
from langchain_core.runnables import RunnableConfig

from langfuse.langchain import CallbackHandler

from app.agents.calendar_agent import get_calendar_agent
from app.agents.triage_agent import build_handoff_graph
from mcp_client import connect_hotel_agent
import config
from config import llm


load_dotenv()

DOCKER_SANDBOX_IMAGE = os.getenv("DOCKER_SANDBOX_IMAGE", "python:3.11-slim")

langfuse_handler = CallbackHandler()



system_message = SystemMessage(
    content="""
    You are the main orchestrator.

    You have access to two specialist agents:

    1. hotel_agent_tool
    - Handle hotel-related requests.

    2. calendar_agent_tool
    - Handle calendar and scheduling requests.

    Rules:

    - Delegate hotel tasks to hotel_agent_tool.
    - Delegate calendar tasks to calendar_agent_tool.
    - Do not perform hotel or calendar operations yourself.
    - If multiple independent tasks are needed, you may call multiple agents.
    - After receiving tool results, decide whether more delegation is necessary.
    - When all requested work is complete, answer the user.
    """
)


_hotel_agent_pool: dict[str, object] = {}
_hotel_exit_stacks: dict[str, AsyncExitStack] = {}
_hotel_locks: dict[str, "asyncio.Lock"] = {}
_mcp_stack: AsyncExitStack | None = None


async def initialize_mcp_stack() -> None:
    global _mcp_stack
    if _mcp_stack is None:
        _mcp_stack = AsyncExitStack()
        await _mcp_stack.__aenter__()


async def close_mcp_stack() -> None:
    global _mcp_stack
    if _mcp_stack is not None:
        await _mcp_stack.aclose()
        _mcp_stack = None


async def get_hotel_agent_for_thread(thread_id: str, user_id: str):
    
    
    

    lock = _hotel_locks.setdefault(thread_id, asyncio.Lock())
    async with lock:
        agent = _hotel_agent_pool.get(thread_id)
        if agent is None:
            if _mcp_stack is None:
                raise RuntimeError("MCP stack is not initialized")

            agent = await connect_hotel_agent(user_id, _mcp_stack)

            _hotel_agent_pool[thread_id] = agent

            logger.info(f"[hotel_mcp] opened session for thread={thread_id} user_id={user_id}")

        return agent


# async def close_hotel_agent_for_thread(thread_id: str):
#     stack = _hotel_exit_stacks.pop(thread_id, None)
#     _hotel_agent_pool.pop(thread_id, None)
#     _hotel_locks.pop(thread_id, None)

#     if stack is not None:
#         try:
#             await stack.aclose()
#             logger.info(f"[hotel_mcp] closed session for thread={thread_id}")
#         except Exception as e:
#             logger.warning(f"[hotel_mcp] error closing session thread={thread_id}: {e}")


@tool
async def transfer_to_hotel_agent_tool(
    task_description: str,
    config: RunnableConfig,
) -> str:
    """Call the hotel agent to handle hotel-related tasks."""

    thread_id = config["configurable"]["thread_id"]
    user_id = config["configurable"]["user_id"]

    agent = await get_hotel_agent_for_thread(thread_id, user_id)

    result = await agent.ainvoke(
        {
            "messages": [
                HumanMessage(content=task_description)
            ]
        },
        config=config,
    )

    return result["messages"][-1].content





@tool
async def transfer_to_calendar_agent_tool(
    task_description: str,
    config: RunnableConfig,
) -> str:
    """Call the calendar agent to handle calendar-related tasks."""

    result = await get_calendar_agent().ainvoke(
        {
            "messages": [
                HumanMessage(content=task_description)
            ]
        },
        config=config,
    )

    return result["messages"][-1].content






_agent_pool: dict[str, object] = {}


# def get_sandbox_for_thread(thread_id: str) -> DockerSandbox:
#     sandbox = _sandbox_pool.get(thread_id)
#     if sandbox is None:
#         sandbox = DockerSandbox(image=DOCKER_SANDBOX_IMAGE)
#         _sandbox_pool[thread_id] = sandbox
#         logger.info(f"[sandbox] created new Docker container for thread={thread_id}")
#     return sandbox


def get_agent_for_thread(thread_id: str):
    agent = _agent_pool.get(thread_id)
    if agent is None:
        

        agent = create_agent(
            model=llm,
            tools=[
                transfer_to_hotel_agent_tool,
                transfer_to_calendar_agent_tool,
            ],
            system_prompt=system_message.content,
           
            checkpointer=config.checkpointer,
        )

        _agent_pool[thread_id] = agent

    return agent


_locks: dict[str, "asyncio.Lock"] = {}
_swarm_pool: dict[str, object] = {}

async def get_swarm_for_thread(thread_id: str, user_id: str):
    lock = _locks.setdefault(thread_id, asyncio.Lock())
    async with lock:
        app = _swarm_pool.get(thread_id)
        if app is not None:
            return app
        calendar_agent = get_calendar_agent()
        hotel_agent = await get_hotel_agent_for_thread(thread_id, user_id)
        app = build_handoff_graph(llm, config.checkpointer, hotel_agent, calendar_agent)

        _swarm_pool[thread_id] = app
        return app

def new_thread(
    user_id: str,
    thread_id: str | None = None,
):
    if not thread_id or not thread_id.strip():
        thread_id = str(uuid.uuid4())

    return {
        "configurable": {
            "thread_id": thread_id,
            "user_id": user_id,
        },
        "callbacks": [
            langfuse_handler
        ],
    }


async def _remove_incomplete_tool_calls(agent, config_: dict) -> None:
    snapshot = await agent.aget_state(config_)
    messages = snapshot.values.get("messages", [])
    tool_call_message_ids: dict[str, str] = {}
    tool_response_message_ids: dict[str, str] = {}
    invalid_message_ids: set[str] = set()

    for message in messages:
        if isinstance(message, AIMessage) and message.tool_calls:
            for tool_call in message.tool_calls:
                if tool_call.get("id"):
                    tool_call_message_ids[tool_call["id"]] = message.id
        elif isinstance(message, ToolMessage):
            tool_response_message_ids[message.tool_call_id] = message.id

    incomplete_tool_call_ids = set(tool_call_message_ids) - set(tool_response_message_ids)
    orphan_tool_call_ids = set(tool_response_message_ids) - set(tool_call_message_ids)
    if incomplete_tool_call_ids or orphan_tool_call_ids:
        invalid_message_ids.update(
            tool_call_message_ids[tool_call_id]
            for tool_call_id in incomplete_tool_call_ids
        )
        invalid_message_ids.update(
            tool_response_message_ids[tool_call_id]
            for tool_call_id in orphan_tool_call_ids
        )
        await agent.aupdate_state(
            config_,
            {"messages": [RemoveMessage(id=message_id) for message_id in invalid_message_ids]},
        )


async def ask_agent(
    question: str,
    user_id: str,
    session_id: str | None = None,
):

    config = new_thread(
        user_id=user_id,
        thread_id=session_id,
    )

    thread_id = config["configurable"]["thread_id"]
    agent = await get_swarm_for_thread(thread_id, user_id)
    await _remove_incomplete_tool_calls(agent, config)

    result = await agent.ainvoke(
        {
            "messages": [
                HumanMessage(
                    content=question
                )
            ]
        },
        config=config,
    )

    return _format_result(result, config)


# async def ask_agent_stream(
#     question: str,
#     user_id: str,
#     session_id: str | None = None,
# ):
#     config = new_thread(
#         user_id=user_id.strip(),
#         thread_id=session_id,
#     )

#     thread_id = config["configurable"]["thread_id"]
#     agent = get_agent_for_thread(thread_id)

#     try:
#         async for stream_mode, payload in agent.astream(
#             {"messages": [HumanMessage(content=question)]},
#             config=config,
#             stream_mode=["messages", "updates"],
#         ):


#             if stream_mode == "messages":
#                 chunk, metadata = payload
#                 node = metadata.get("langgraph_node", "")


#                 content = getattr(chunk, "content", None)
#                 if content:
#                     print(f"[NODE: {node}]")
#                     print(content, end="", flush=True)

#                     yield {
#                         "type": "token",
#                         "node": node,
#                         "content": content,
#                     }

#                 tool_call_chunks = getattr(chunk, "tool_call_chunks", None)
#                 if tool_call_chunks:
#                     for tc in tool_call_chunks:
#                         if tc.get("name"):
#                             print(f"\n[TOOL CALL START] name={tc['name']}")

#                             yield {
#                                 "type": "tool_call_start",
#                                 "node": node,
#                                 "tool_call_id": tc.get("id"),
#                                 "name": tc["name"],
#                             }

#                 if isinstance(chunk, ToolMessage):
#                     print(f"\n[TOOL END] {chunk.name}")
#                     print(chunk.content)

#                     yield {
#                         "type": "tool_end",
#                         "node": node,
#                         "tool": chunk.name,
#                         "tool_call_id": chunk.tool_call_id,
#                         "output": chunk.content,
#                     }


#             elif stream_mode == "updates":
#                 for node_name, node_output in payload.items():
#                     if node_name == "__interrupt__":
#                         print(f"\n[INTERRUPT] {node_output}")
#                         yield {
#                             "type": "interrupt",
#                             "output": node_output,
#                         }
#                         continue

#                     print(f"\n[NODE UPDATE] {node_name}")
#                     print(node_output)

#                     yield {
#                         "type": "node_update",
#                         "node": node_name,
#                         "output": node_output,
#                     }

#         yield {
#             "type": "done",
#         }

#     except Exception as e:
#         print("\nSTREAM ERROR:", repr(e))

#         yield {
#             "type": "error",
#             "message": str(e),
#         }


# async def resume_agent(
#     user_id: str,
#     session_id: str,
#     approved: bool | None = None,
#     interrupt_id: str = "",
#     reason: str | None = None,
#     input: str | None = None,
# ):
#     config = new_thread(
#         user_id=user_id,
#         thread_id=session_id,
#     )

#     thread_id = config["configurable"]["thread_id"]
#     agent = get_agent_for_thread(thread_id)

#     if input is not None:

#         resume_payload = input


#     else:

#         if approved is True:
#             decision = {
#                 "type": "approve",
#             }

#         elif approved is False:
#             decision = {
#                 "type": "reject",
#             }

#             if reason:
#                 decision["message"] = reason

#         else:
#             raise ValueError(
#                 "approved phải được cung cấp khi không có input."
#             )

#         resume_payload = {
#             "decisions": [decision],
#         }

#     logger.info(
#         f"Resuming thread={session_id}, "
#         f"interrupt_id={interrupt_id}, "
#         f"payload={resume_payload}"
#     )

#     result = await agent.ainvoke(
#         Command(resume=resume_payload),
#         config=config,
#     )

#     logger.info(result)

#     return _format_result(result, config)


def _format_result(result: dict, config: dict):

    thread_id = config["configurable"]["thread_id"]

    interrupts = result.get("__interrupt__")
    if interrupts:
        for interrupt_item in interrupts:
            logger.info(f"interrupt value: {interrupt_item.value}")

    if interrupts:
        approvals = []

        for interrupt_item in interrupts:
            approvals.append(
                {
                    "interrupt_id": interrupt_item.id,
                    "approval_request": interrupt_item.value,
                }
            )

        return {
            "status": "pending_approval",
            "approvals": approvals,
            "session_id": thread_id,
        }



    answer = result["messages"][-1].content



    return {
        "status": "done",
        "answer": answer,
        "session_id": thread_id,
        "approvals": [],
    }



