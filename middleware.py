"""
Middleware chống lỗi:
    "messages with role 'tool' must be a response to a preceding
     message with 'tool_calls'"

Nguyên nhân: state["messages"] được share giữa nhiều agent trong swarm
(triage_agent -> hotel_agent -> calendar_agent). Nếu 1 turn bị ngắt giữa
chừng (exception, MCP timeout, restart process...) ngay sau khi model
sinh AIMessage(tool_calls=...) nhưng trước khi ToolMessage tương ứng
được ghi vào state, cặp tool_call/tool_response bị "gãy" sẽ tồn tại mãi
trong checkpoint và làm hỏng MỌI request kế tiếp gửi lên Azure OpenAI.

Khác với `_remove_incomplete_tool_calls()` (chỉ chạy 1 lần ở đầu
`ask_agent`, trên state graph tổng), middleware này chạy NGAY TRƯỚC
MỖI lần gọi model, ở TỪNG agent con -> chặn lỗi bất kể nó phát sinh ở
đâu, kể cả giữa turn hiện tại.

Cách dùng: thêm vào middleware=[...] của MỌI create_agent() có tool-calling
(triage_agent, hotel_agent, calendar_agent).
"""

from typing import Any

from langchain.agents.middleware import AgentMiddleware, AgentState
from langchain_core.messages import AIMessage, RemoveMessage, ToolMessage
from langgraph.runtime import Runtime


class SanitizeToolCallsMiddleware(AgentMiddleware):
    """Loại bỏ AIMessage(tool_calls=...) không có ToolMessage phản hồi,
    và ToolMessage mồ côi (không có AIMessage.tool_calls tương ứng),
    ngay trước khi state được gửi cho model."""

    def before_model(self, state: AgentState, runtime: Runtime) -> dict[str, Any] | None:
        messages = state.get("messages", [])

        tool_call_owner: dict[str, str] = {}   # tool_call_id -> id của AIMessage chứa nó
        tool_response_owner: dict[str, str] = {}  # tool_call_id -> id của ToolMessage phản hồi

        for message in messages:
            if isinstance(message, AIMessage) and message.tool_calls:
                for tool_call in message.tool_calls:
                    call_id = tool_call.get("id")
                    if call_id:
                        tool_call_owner[call_id] = message.id
            elif isinstance(message, ToolMessage):
                tool_response_owner[message.tool_call_id] = message.id

        incomplete_ids = set(tool_call_owner) - set(tool_response_owner)  # gọi tool nhưng chưa có response
        orphan_ids = set(tool_response_owner) - set(tool_call_owner)      # response nhưng không có tool_call

        if not incomplete_ids and not orphan_ids:
            return None

        invalid_message_ids: set[str] = set()
        invalid_message_ids.update(tool_call_owner[i] for i in incomplete_ids)
        invalid_message_ids.update(tool_response_owner[i] for i in orphan_ids)

        return {
            "messages": [RemoveMessage(id=mid) for mid in invalid_message_ids],
        }