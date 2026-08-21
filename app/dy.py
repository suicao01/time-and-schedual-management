# init_db.py
from model import Base
from config import engine  # engine bạn dùng để tạo SessionLocal

def init_db():
    Base.metadata.create_all(bind=engine)
    print("Đã tạo xong bảng (nếu chưa có).")

if __name__ == "__main__":
    from datetime import datetime

# Lấy ngày và giờ hiện tại
    now = datetime.now()
    print("Ngày giờ hiện tại:", now)
