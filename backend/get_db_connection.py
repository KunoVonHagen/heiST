from dotenv import load_dotenv
import psycopg2
import os
from contextlib import contextmanager
from typing import Generator

load_dotenv()

# Database connection parameters
DB_HOST: str = os.getenv("DB_HOST", "localhost")
DB_NAME: str = os.getenv("DB_NAME", "exampledb")
DB_USER: str = os.getenv("DB_USER", "postgres")
DB_PASSWORD: str = os.getenv("DB_PASSWORD", "changeme")

def get_db_connection() -> psycopg2.extensions.connection:
    """
    Establish a connection to the PostgreSQL database.
    """
    print("[DB] Opening new database connection")


    db_conn: psycopg2.extensions.connection = psycopg2.connect(
        host=DB_HOST,
        database=DB_NAME,
        user=DB_USER,
        password=DB_PASSWORD
    )
    db_conn.autocommit = True
    return db_conn


@contextmanager
def db_connection_context() -> Generator[psycopg2.extensions.connection, None, None]:
    """
    Provide a managed PostgreSQL connection and always close it.
    """
    db_conn: psycopg2.extensions.connection = get_db_connection()
    try:
        yield db_conn
    finally:
        db_conn.close()
