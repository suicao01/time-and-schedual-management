from langgraph.graph import MessagesState
from langgraph.checkpoint.base import BaseCheckpointSaver
from langgraph_swarm import create_swarm, create_handoff_tool
from langchain.agents import create_agent
from middleware import SanitizeToolCallsMiddleware


class SwarmState(MessagesState):
    active_agent: str


def build_handoff_graph(llm, checkpointer, hotel_agent, calendar_agent):
    transfer_to_hotel = create_handoff_tool(
        agent_name="hotel_agent",
        description="Chuyển yêu cầu liên quan khách sạn sang hotel_agent.",
    )
    transfer_to_calendar = create_handoff_tool(
        agent_name="calendar_agent",
        description="Chuyển yêu cầu liên quan lịch/calendar sang calendar_agent.",
    )
    transfer_to_triage = create_handoff_tool(
        agent_name="triage_agent",
        description="Chuyển lại cho triage_agent khi việc ngoài phạm vi agent hiện tại.",
    )

    triage_agent = create_agent(
        model=llm.bind(parallel_tool_calls=False),
        tools=[transfer_to_hotel, transfer_to_calendar],
        system_prompt="Bạn là orchestrator. Luôn handoff, không tự xử lý nghiệp vụ.",
        name="triage_agent",
        middleware=[SanitizeToolCallsMiddleware()],

    )

   
    workflow = create_swarm(
        agents=[triage_agent, hotel_agent, calendar_agent],
        default_active_agent="triage_agent",
        state_schema=SwarmState,
    )

    return workflow.compile(checkpointer=checkpointer)