# init_db.py
from app.model import Base
from config import engine  # engine bạn dùng để tạo SessionLocal

def init_db():
    Base.metadata.create_all(bind=engine)
    print("Đã tạo xong bảng (nếu chưa có).")

if __name__ == "__main__":
    init_db()
