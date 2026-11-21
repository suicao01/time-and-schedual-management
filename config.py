import os

from dotenv import load_dotenv
from langchain_openai import AzureChatOpenAI
from psycopg.rows import dict_row
from psycopg_pool import AsyncConnectionPool
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.orm import DeclarativeBase
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver

load_dotenv()
DATABASE_URL = os.getenv("DATABASE_URL")
if DATABASE_URL:
    DATABASE_URL = DATABASE_URL.replace("postgresql+psycopg2://", "postgresql+psycopg://", 1)
    DATABASE_URL = DATABASE_URL.replace("postgresql://", "postgresql+psycopg://", 1)
engine = create_engine(DATABASE_URL)


checkpoint_database_url = DATABASE_URL.replace("postgresql+psycopg://", "postgresql://", 1)
checkpoint_pool = AsyncConnectionPool(
    conninfo=checkpoint_database_url,
    kwargs={
        "autocommit": True,
        "prepare_threshold": 0,
        "row_factory": dict_row,
    },
    open=False,
)
checkpointer = None


async def initialize_checkpointer():
    global checkpointer

    await checkpoint_pool.open()
    checkpointer = AsyncPostgresSaver(conn=checkpoint_pool)
    await checkpointer.setup()


async def close_checkpointer():
    await checkpoint_pool.close()




AZURE_AI_API_KEY = os.getenv("AZURE_AI_API_KEY")
AZURE_AI_ENDPOINT = os.getenv("AZURE_AI_ENDPOINT")
AZURE_AI_LLM_DEPLOYMENT = os.getenv("AZURE_AI_LLM_DEPLOYMENT")
AZURE_AI_API_VERSION = os.getenv(
    "AZURE_AI_API_VERSION",
    "2024-08-01-preview",
)

llm = AzureChatOpenAI(
    azure_deployment=AZURE_AI_LLM_DEPLOYMENT,
    azure_endpoint=AZURE_AI_ENDPOINT,
    api_key=AZURE_AI_API_KEY,
    api_version=AZURE_AI_API_VERSION,
    temperature=0,
)


SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

class Base(DeclarativeBase):
  pass

# Dependency để dùng trong FastAPI sau này
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()