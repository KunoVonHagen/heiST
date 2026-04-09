import subprocess
import os
from dotenv import load_dotenv, find_dotenv
from get_db_connection import db_connection_context
from typing import Tuple
import psycopg2

load_dotenv(find_dotenv())

CHALLENGES_ROOT_SUBNET: str = os.getenv("CHALLENGES_ROOT_SUBNET", "10.128.0.0")
CHALLENGES_ROOT_SUBNET_MASK: str = os.getenv("CHALLENGES_ROOT_SUBNET_MASK", "255.128.0.0")
CHALLENGES_ROOT_SUBNET_MASK_INT: int = sum(bin(int(x)).count('1') for x in CHALLENGES_ROOT_SUBNET_MASK.split('.'))
CHALLENGES_ROOT_SUBNET_CIDR: str = f"{CHALLENGES_ROOT_SUBNET}/{CHALLENGES_ROOT_SUBNET_MASK_INT}"


def stop_challenge(user_id: int) -> None:
    """
    Stop a challenge for a user.
    """

    with db_connection_context() as db_conn:
        user_static_ip: str
        challenge_id: int
        user_static_ip, challenge_id = get_user_static_ip_and_challenge_id(user_id, db_conn)
        remove_user_iptables_rules(user_static_ip)
        mark_challenge_expired(challenge_id, db_conn)
        unassign_challenge_from_user(user_id, db_conn)


def get_user_static_ip_and_challenge_id(user_id: int, db_conn: psycopg2.extensions.connection) -> Tuple[str, int]:
    """
    Get the running challenge ID for a user.
    """
    with db_conn.cursor() as cursor:
        cursor.execute("""
            SELECT vpn_static_ip, running_challenge
            FROM users
            WHERE id = %s
        """, (user_id,))

        result: Tuple[str, int] | None = cursor.fetchone()
        if not result:
            raise Exception(f"No running challenge found for user ID {user_id}")

        return result[0], result[1]


def mark_challenge_expired(challenge_id: int, db_conn: psycopg2.extensions.connection) -> None:
    """
    Mark the challenge as expired in the database.
    """
    with db_conn.cursor() as cursor:
        cursor.execute("""
            UPDATE challenges
            SET lifecycle_state = 'EXPIRED'
            WHERE id = %s
        """, (challenge_id,))


def remove_user_iptables_rules(user_static_ip: str) -> None:
    """
    Remove all iptables rules that contain the user's static IP.
    """
    # Get all iptables rules
    result: subprocess.CompletedProcess[str] = subprocess.run(["sudo", "iptables", "-S"], capture_output=True, text=True)
    rules: list[str] = result.stdout.splitlines()

    # Filter rules that contain the user's static IP
    rules_to_remove: list[str] = [rule for rule in rules if user_static_ip in rule]

    # Remove each rule
    for rule in rules_to_remove:
        delete_rule: str = rule.replace("-A", "-D")  # Change -A to -D to delete the rule
        subprocess.run(["sudo", "iptables"] + delete_rule.split(), check=True, capture_output=True)


def unassign_challenge_from_user(user_id: int, db_conn: psycopg2.extensions.connection) -> None:
    """
    Unassign the challenge from the user in the database.
    """
    with db_conn.cursor() as cursor:
        cursor.execute("""
            UPDATE users
            SET running_challenge = NULL
            WHERE id = %s
        """, (user_id,))
