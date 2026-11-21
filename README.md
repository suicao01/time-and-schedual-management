# Booking

Hệ thống đặt phòng khách sạn sử dụng FastAPI, LangGraph, Agents và MCP.

## Mô tả dự án

Booking là hệ thống đặt phòng khách sạn kết hợp API truyền thống với hệ thống agent AI có khả năng hiểu ngôn ngữ tự nhiên. Người dùng có thể khai báo thông tin khách sạn, tìm kiếm nơi lưu trú phù hợp và thực hiện đặt phòng thông qua HTTP API hoặc tương tác trực tiếp với agent.

Hệ thống sử dụng FastAPI làm lớp tiếp nhận yêu cầu, PostgreSQL và SQLAlchemy để lưu trữ dữ liệu, Alembic để quản lý thay đổi cơ sở dữ liệu. Lớp AI được xây dựng bằng LangChain, LangGraph và Deep Agents; các thao tác nghiệp vụ khách sạn được cung cấp dưới dạng công cụ MCP (Model Context Protocol), giúp agent truy xuất dữ liệu và thực thi hành động có kiểm soát.

## Kiến trúc

- **FastAPI**: Cung cấp REST API, quản lý vòng đời ứng dụng và dependency cho truy cập cơ sở dữ liệu.
- **SQLAlchemy**: Ánh xạ dữ liệu khách sạn, người dùng, booking, sự kiện và thực hiện truy vấn PostgreSQL.
- **Alembic**: Tạo và theo dõi các migration cho schema cơ sở dữ liệu.
- **LangGraph/Deep Agents**: Điều phối luồng hội thoại, phân tích ý định và chuyển yêu cầu giữa các agent chuyên trách.
- **MCP Server**: Cung cấp các tool tìm kiếm khách sạn, tạo đặt phòng và hủy đặt phòng.
- **Langfuse**: Theo dõi, kiểm tra và đánh giá các lần gọi mô hình và luồng agent.
- **PostgreSQL Checkpointer**: Lưu trạng thái hội thoại để hỗ trợ xử lý theo phiên và chuỗi tương tác liên tục.

## Luồng xử lý

1. Client gọi API `/ask` kèm câu hỏi, `user_id` và `session_id`.
2. FastAPI khởi tạo hoặc phục hồi trạng thái hội thoại từ PostgreSQL checkpointer.
3. Orchestrator phân tích yêu cầu và định tuyến tới agent phù hợp.
4. Agent lựa chọn công cụ MCP cần thiết để tìm khách sạn, tạo booking hoặc hủy booking.
5. Các thao tác cơ sở dữ liệu được thực hiện qua SQLAlchemy trong cùng ngữ cảnh người dùng hiện tại.
6. Kết quả được tổng hợp thành phản hồi có cấu trúc và trả về cho client.

## Các API chính

- `POST /users`: Tạo người dùng mới.
- `POST /hotels`: Thêm hoặc cập nhật thông tin khách sạn.
- `POST /events`: Tạo sự kiện hoặc lịch liên quan đến booking.
- `POST /ask`: Gửi yêu cầu bằng ngôn ngữ tự nhiên cho hệ thống agent.

## Công cụ MCP

- Tìm kiếm khách sạn theo tên, địa điểm hoặc mô tả.
- Tạo đặt phòng với hotel, thời gian bắt đầu và thời gian kết thúc.
- Hủy đặt phòng theo booking ID, có kiểm tra quyền sở hữu.

## Quản lý dữ liệu

Các thực thể chính bao gồm:

- **User**: Thông tin người dùng và danh sách đặt phòng.
- **Hotel**: Tên, mô tả và vị trí khách sạn.
- **Booking**: Liên kết người dùng với khách sạn, thời gian nhận/trả phòng.
- **Event**: Sự kiện hoặc khoảng thời gian phục vụ logic lịch.

## Yêu cầu môi trường

- Python 3.12 trở lên
- PostgreSQL
- Công cụ `uv`
- API key của nhà cung cấp mô hình AI
- Thông tin kết nối Langfuse nếu bật tracing

## Cấu hình

Tạo file `.env` trong thư mục gốc và cấu hình các biến môi trường cần thiết cho PostgreSQL, API model, Langfuse và MCP transport. Không commit file `.env` lên hệ thống quản lý mã nguồn.

## Chạy ứng dụng

```powershell
uv sync
uv run uvicorn app.main:app --reload
```