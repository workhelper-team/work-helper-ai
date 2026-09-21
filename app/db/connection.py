import os
import psycopg
from dotenv import load_dotenv

load_dotenv()

# DB 커넥션 생성 및 연결
def get_db_connection():
    return psycopg.connect(
        host = os.getenv("POSTGRES_HOST"),
        port= os.getenv("POSTGRES_PORT", "5432"),
        dbname = os.getenv("POSTGRES_DB", "workhelper"),
        user = os.getenv("POSTGRES_USER", "postgres"),
        password = os.getenv("POSTGRES_PASSWORD")
    )