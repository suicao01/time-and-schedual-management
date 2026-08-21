from typing import Annotated
from typing_extensions import TypedDict

import uuid
from dotenv import load_dotenv
import os
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.graph.message import add_messages
from langgraph.graph import StateGraph, START, END
from datetime import datetime
from langchain_openai import AzureChatOpenAI
from langchain_core.messages import ToolMessage, HumanMessage, SystemMessage

from langfuse.langchain import CallbackHandler

from create_event import create_event
from delete_event import delete_event
from list_events import list_events
from update_event import update_event



load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")
AZURE_AI_API_KEY = os.getenv("AZURE_AI_API_KEY")
AZURE_AI_ENDPOINT = os.getenv("AZURE_AI_ENDPOINT")
AZURE_AI_LLM_DEPLOYMENT = os.getenv("AZURE_AI_LLM_DEPLOYMENT")
AZURE_AI_API_VERSION = os.getenv("AZURE_AI_API_VERSION", "2024-08-01-preview")


langfuse_handler = CallbackHandler()


llm = AzureChatOpenAI(
    azure_deployment=AZURE_AI_LLM_DEPLOYMENT,
    azure_endpoint=AZURE_AI_ENDPOINT,
    api_key=AZURE_AI_API_KEY,
    api_version = AZURE_AI_API_VERSION,
    temperature=0,
)


tools = [
    create_event,
    update_event,
    delete_event,
    list_events,
]

tools_by_name = {tool.name: tool for tool in tools}

llm_with_tools = llm.bind_tools(tools)


# Lấy ngày và giờ hiện tại
now = datetime.now()


system_messages = SystemMessage(content= f"Thời gian hiện tại {now}. Khi user hỏi ngày mai, hôm qua dựa theo thông tin trên để trả lời")

# state
class AgentState(TypedDict):
    messages: Annotated[list, add_messages]


def llm_node(state: AgentState, config):
    message = state["messages"] + [system_messages]
    response = llm_with_tools.invoke(
        message,
        config=config,
    )
    return {"messages": [response]}


def tool_node(state: AgentState):
    last_message = state["messages"][-1]
    tool_messages = []

    for tool_call in last_message.tool_calls:
        tool_name = tool_call["name"]
        tool_args = tool_call["args"]
        tool = tools_by_name[tool_name]
        result = tool.invoke(tool_args)

        tool_messages.append(
            ToolMessage(content=str(result), tool_call_id=tool_call["id"])
        )

    return {"messages": tool_messages}


def should_continue(state: AgentState):
    last_message = state["messages"][-1]
    if last_message.tool_calls:
        return "tools"
    return "end"


graph_builder = StateGraph(AgentState)

graph_builder.add_node("llm", llm_node)
graph_builder.add_node("tools", tool_node)

graph_builder.add_edge(START, "llm")
graph_builder.add_conditional_edges(
    "llm",
    should_continue,
    {"tools": "tools", "end": END},
)
graph_builder.add_edge("tools", "llm")

checkpointer = InMemorySaver()
graph = graph_builder.compile(checkpointer=checkpointer)


def new_thread(thread_id: str | None = None) -> dict:
    return {
        "configurable": {"thread_id": thread_id or str(uuid.uuid4())},
        "callbacks": [langfuse_handler],
    }


if __name__ == "__main__":
    config = new_thread()
    print("Thread:", config["configurable"]["thread_id"])
    print("Lệnh: 'new' = mở thread mới | 'exit' = thoát\n")

    while True:
        user_input = input("Bạn: ").strip()
        if user_input.lower() in {"exit", "quit"}:
            break
        if user_input.lower() == "new":
            config = new_thread()
            print("-> Thread mới:", config["configurable"]["thread_id"])
            continue

        result = graph.invoke(
            {"messages": [HumanMessage(content=user_input)]},
            config=config,
        )
        print("Agent:", result["messages"][-1].content, "\n")