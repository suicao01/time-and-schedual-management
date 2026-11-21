from langgraph_swarm import create_handoff_tool

def hand_off_tool(agent_name: str, description: str | None):
    return create_handoff_tool(
        agent_name=agent_name,
        description=description,
    )
        
transfer_to_hotel_agent_tool = hand_off_tool(
    agent_name="hotel_agent",
    
    description="Transfer the conversation to the hotel agent.")
transfer_to_calendar_agent_tool = hand_off_tool(
    agent_name="calendar_agent",
    
    description="Transfer the conversation to the calendar agent.")
transfer_to_triage_agent_tool = hand_off_tool(
    agent_name="triage_agent",
    
    description="Transfer the conversation to the triage agent.")