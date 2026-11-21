import json
from typing import Any

from dotenv import load_dotenv
import os
from datetime import datetime
from app.tools.handoff_tool import transfer_to_triage_agent_tool
from langchain_openai import AzureChatOpenAI
from langchain_core.messages import ToolMessage, SystemMessage
from langchain.agents import create_agent
from langchain.agents.middleware import (
    AgentMiddleware,
    AgentState,
   
)
from middleware import SanitizeToolCallsMiddleware
from langgraph.runtime import Runtime
from langfuse.langchain import CallbackHandler
from loguru import logger
import config
from config import AZURE_AI_LLM_DEPLOYMENT, AZURE_AI_ENDPOINT, AZURE_AI_API_KEY, AZURE_AI_API_VERSION, llm

from app.tools.calendar_tools import (
    create_event,
    update_event,
    delete_event,
    list_events,
)


load_dotenv()




langfuse_handler = CallbackHandler()




now = datetime.now()

system_messages = SystemMessage(
    content=f"""
You are a calendar agent.
Hand off to the triage agent if the user's request is not related to calendar events.
Your tasks include:
- create calendar events
- list calendar events
- update calendar events
- delete calendar events

NOTE:
Use timestamp {now} to resolve user requests about
today, tomorrow, yesterday, etc.
"""
)




class LoggingMiddleware(AgentMiddleware):
    """Log khi agent bắt đầu và kết thúc xử lý."""

    def before_agent(self, state: AgentState, runtime: Runtime) -> None:
        print(f"[LOG] Agent bắt đầu xử lý. Input: {state['messages'][-1] if state['messages'] else None}")

    def after_agent(self, state: AgentState, runtime: Runtime) -> None:
        final_message = state["messages"][-1] if state["messages"] else None
        print(f"[LOG] Agent kết thúc xử lý. Kết quả cuối: {final_message}")



def get_calendar_agent():
    

    
    agent_tools = [
            create_event,
            update_event,
            delete_event,
            list_events,
            transfer_to_triage_agent_tool,
        ]
    calendar_agent = create_agent(
        model=llm.bind(parallel_tool_calls=False),
        tools=agent_tools,
        system_prompt=system_messages.content,
        name="calendar_agent",
        middleware=[LoggingMiddleware(), SanitizeToolCallsMiddleware()],
        )

    return calendar_agent