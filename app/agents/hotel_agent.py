import re
from typing import Any
from datetime import datetime

from langgraph.runtime import Runtime
from langchain_openai import AzureChatOpenAI
from langchain_core.messages import AIMessage, SystemMessage
from langchain.agents import create_agent
from langchain.agents.middleware import AgentMiddleware, AgentState
from middleware import SanitizeToolCallsMiddleware

import config
from config import (
 
    llm
)



now = datetime.now()

system_messages = SystemMessage(content=f"""
Thời gian hiện tại: {now}.
Khi user hỏi về "hôm nay", "ngày mai", "hôm qua", hãy dựa vào thời gian hiện tại ở trên để tính toán và trả lời chính xác.
Hand off cho triage agent nếu yeu cau của user không liên quan đến đặt phòng khách sạn.
Khi user hỏi về khách sạn theo địa danh (dùng tên đầy đủ, tên viết tắt, hoặc tên gọi khác của địa danh), hãy tự động nhận diện và ánh xạ sang đúng mã location tương ứng trong bảng trước khi truy vấn/lọc dữ liệu. Bảng ánh xạ tham khảo (mở rộng nếu gặp địa danh khác không có trong danh sách, dùng mã viết tắt hợp lý theo quy tắc chữ cái đầu):

- Hà Nội → HN
- Hồ Chí Minh / Sài Gòn → HCM
- Đà Nẵng → DN
- Hải Phòng → HP
- Cần Thơ → CT
- Nha Trang → NT
- Đà Lạt → DL
- Huế → HUE
- Vũng Tàu → VT
- Phú Quốc → PQ
- Quy Nhơn → QN
- Hạ Long → HL

Quy tắc xử lý:
1. Nếu user nhập tên địa danh không dấu, viết tắt, viết hoa/thường lẫn lộn -> ánh xạ sang mã chuẩn.
2. Nếu không chắc chắn địa danh nào được nhắc đến, hỏi lại user để làm rõ thay vì đoán.
3. Khi trả lời, chỉ lọc kết quả theo đúng mã location đã ánh xạ, không suy diễn thêm địa danh khác.
4. Nếu địa danh user hỏi không có trong dữ liệu, thông báo rõ là không tìm thấy khách sạn tại địa danh đó.
""")


class HotelMiddleware(AgentMiddleware):

    def extract_booking_dates(self, text: str):
        pattern = re.compile(
            r"(?:từ|tu|from)\s*(?:ngày\s*)?"
            r"(\d{1,2}[/-]\d{1,2}(?:[/-]\d{4})?)"
            r"\s*(?:đến|toi|to|-)\s*"
            r"(?:ngày\s*)?"
            r"(\d{1,2}[/-]\d{1,2}(?:[/-]\d{4})?)",
            re.IGNORECASE,
        )
        match = pattern.search(text)
        if not match:
            return None, None
        return match.group(1), match.group(2)

    def parse_date(self, date_str: str):
        for fmt in ("%d/%m/%Y", "%d-%m-%Y", "%d/%m", "%d-%m"):
            try:
                date = datetime.strptime(date_str, fmt)
                if "%Y" not in fmt:
                    date = date.replace(year=datetime.now().year)
                return date
            except ValueError:
                continue
        return None

    async def abefore_agent(
        self,
        state: AgentState,
        runtime: Runtime,
    ) -> dict[str, Any] | None:

        messages = state["messages"]
        if not messages:
            return None

        content = messages[-1].content
        check_in_str, check_out_str = self.extract_booking_dates(content)

        if not check_in_str or not check_out_str:
            return None

        check_in = self.parse_date(check_in_str)
        check_out = self.parse_date(check_out_str)

        if check_in is None or check_out is None:
            return {
                "messages": [
                    AIMessage(content="Thông tin ngày đặt phòng không hợp lệ. ")
                ]
            }

        if check_in < datetime.now():
            return {
                "messages": [
                    AIMessage(
                        content=(
                            f"Ngày check-in {check_in.strftime('%d/%m/%Y')} đã qua. "
                            f"Hãy yêu cầu user nhập lại ngày check-in và check-out. "
                            f"Không được gọi hotel tool."
                        )
                    )
                ]
            }
        return None




def build_hotel_agent(tools: list):
    return create_agent(
        model=llm.bind(parallel_tool_calls=False),
        tools=tools,
        system_prompt=system_messages.content,
        middleware=[SanitizeToolCallsMiddleware()],
        name="hotel_agent",
    )