import os
import fcntl
from typing import List
import psycopg2
import threading
from dotenv import load_dotenv

from .stop_challenge import stop_challenge
from .teardown_challenge import teardown_challenge

load_dotenv()

DATABASE_HOST: str = os.getenv("DB_HOST", "10.0.0.102")
DATABASE_PORT: str = os.getenv("DB_PORT", "5432")
DATABASE_USER: str = os.getenv("DB_USER", "postgres")
DATABASE_PASSWORD: str = os.getenv("DB_PASSWORD", "changeme")
DATABASE_NAME: str = os.getenv("DB_NAME", "ctf_challenger")

CLEANUP_COMPLETE_FILE_PATH: str = "/var/lock/cleanup_complete.lock"
if not os.path.exists(CLEANUP_COMPLETE_FILE_PATH):
    with open(CLEANUP_COMPLETE_FILE_PATH, 'w') as f:
        pass

def cleanup_remaining_challenges() -> None:
    """
    Remove all challenges from the database.
    """
    signal_cleanup_not_complete()

    db_conn = wait_for_db_connection()

    user_ids: List[int] = fetch_user_ids(db_conn)
    stop_running_challenges(user_ids)

    remaining_challenge_ids: List[int] = fetch_remaining_challenge_ids(db_conn)
    teardown_remaining_challenges(remaining_challenge_ids)

    signal_cleanup_complete()


def signal_cleanup_not_complete() -> None:
    """
    Signal that the cleanup process is not complete by acquiring a lock on a file.
    """

    with open(CLEANUP_COMPLETE_FILE_PATH, 'w') as f:
        fcntl.flock(f, fcntl.LOCK_EX) # type: ignore [attr-defined]



def wait_for_db_connection() -> psycopg2.extensions.connection:
    """
    Wait for the database connection to be available.
    """
    import psycopg2

    db_conn: "psycopg2.extensions.connection | None" = None
    while not db_conn:
        try:
            db_conn = psycopg2.connect(
                host=DATABASE_HOST,
                port=DATABASE_PORT,
                user=DATABASE_USER,
                password=DATABASE_PASSWORD,
                dbname=DATABASE_NAME
            )

        except Exception:
            pass

    return db_conn


def fetch_user_ids(db_conn: psycopg2.extensions.connection) -> List[int]:
    """
    Fetch all running challenges from the database.
    """
    with db_conn.cursor() as cursor:
        cursor.execute("SELECT id FROM users WHERE running_challenge IS NOT NULL")
        user_ids: List[int] = [row[0] for row in cursor.fetchall()]

    return user_ids


def stop_running_challenges(user_ids: List[int]) -> None:
    """
    Stop all running challenges for the specified user IDs.
    """

    threads: List[threading.Thread] = []

    for user_id in user_ids:
        thread: threading.Thread = threading.Thread(target=stop_challenge, args=(user_id,))
        thread.start()
        threads.append(thread)

    for thread in threads:
        thread.join()


def fetch_remaining_challenge_ids(db_conn: psycopg2.extensions.connection) -> List[int]:
    """
    Fetch all remaining challenge IDs from the database.
    """
    challenge_ids: List[int] = []
    with db_conn.cursor() as cursor:
        cursor.execute("SELECT id FROM challenges WHERE lifecycle_state != 'EXPIRED'")
        challenge_ids = [row[0] for row in cursor.fetchall()]

    return challenge_ids


def teardown_remaining_challenges(challenge_ids: List[int]) -> None:
    """
    Teardown all remaining challenges.
    """

    threads: List[threading.Thread] = []

    for challenge_id in challenge_ids:
        thread: threading.Thread = threading.Thread(target=teardown_challenge, args=(challenge_id,))
        thread.start()
        threads.append(thread)

    for thread in threads:
        thread.join()


def signal_cleanup_complete() -> None:
    """
    Signal that the cleanup process is complete by releasing the lock on the file.
    """
    with open(CLEANUP_COMPLETE_FILE_PATH, 'w') as f:
        fcntl.flock(f, fcntl.LOCK_UN) # type: ignore [attr-defined]


if __name__ == "__main__":
    cleanup_remaining_challenges()
