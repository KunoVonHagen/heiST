from flask import Flask, request, send_file, redirect, Response, make_response
import psycopg2
from dotenv import load_dotenv
import os
from typing import Dict, Tuple, List

from .cloud_init_ip_pool import ip_pool
from .launch_challenge import launch_challenge as launch_challenge_backend
from .stop_challenge import stop_challenge as stop_challenge_backend
from .import_machine_templates import import_machine_templates as import_machine_template_backend
from .delete_machine_templates import delete_machine_templates as delete_machine_template_backend
from .get_user_config import get_user_config as get_user_config_backend
from .delete_user_config import delete_user_config as delete_user_config_backend

load_dotenv()

app: Flask = Flask(__name__)

# Database connection parameters
DB_HOST: str = os.getenv("DB_HOST", "localhost")
DB_NAME: str = os.getenv("DB_NAME", "exampledb")
DB_USER: str = os.getenv("DB_USER", "postgres")
DB_PASSWORD: str = os.getenv("DB_PASSWORD", "changeme")

BACKEND_HOST: str = os.getenv("BACKEND_HOST", "10.0.0.1")
BACKEND_PORT: str = os.getenv("BACKEND_PORT", "8000")

BACKEND_LOGGING_DIR: str = os.getenv("BACKEND_LOGGING_DIR", "/var/log/backend")

BACKEND_CERTIFICATE_FILE: str = os.getenv("BACKEND_CERTIFICATE_FILE", "/root/ctf-challenger/backend.crt")
BACKEND_CERTIFICATE_KEY_FILE: str = os.getenv("BACKEND_CERTIFICATE_KEY_FILE", "/root/ctf-challenger/backend.key")

BACKEND_AUTHENTICATION_TOKEN: str | None = os.getenv("BACKEND_AUTHENTICATION_TOKEN")

MONITORING_VPN_INTERFACE: str = os.getenv("MONITORING_VPN_INTERFACE", "ctf_monitoring")
MONITORING_DMZ_INTERFACE: str = os.getenv("MONITORING_DMZ_INTERFACE", "dmz_monitoring")

os.makedirs(BACKEND_LOGGING_DIR, exist_ok=True)


def get_db_connection() -> psycopg2.extensions.connection:
    """
    Establish a connection to the PostgreSQL database.
    """
    conn: psycopg2.extensions.connection = psycopg2.connect(
        host=DB_HOST,
        database=DB_NAME,
        user=DB_USER,
        password=DB_PASSWORD
    )
    return conn


@app.before_request
def before_request() -> Tuple[Response, int] | None:
    """
    This function runs before each request to the Flask app.
    First, all http requests are redirected to https.
    It checks if the user is authorized based on the authentication token.
    """

    if not request.is_secure:
        return make_response(redirect(f"https://{request.host}{request.path}", code=301), 301), 301

    authentication_token: str | None = request.headers.get('Authentication-Token')

    if not authentication_token or not authentication_token == BACKEND_AUTHENTICATION_TOKEN:
        print("Unauthorized access attempt", flush=True)
        return make_response({"error": "Unauthorized", "success": False}, 401), 401

    return None


@app.route('/launch-challenge', methods=['POST'])
def launch_challenge() -> Tuple[Response, int]:
    try:
        data: Dict[str, int] | None = request.json
        if not data:
            raise ValueError("No JSON data")
        challenge_template_id: int = int(data['challenge_template_id'])
        user_id: int = int(data['user_id'])
    except Exception as e:
        print("Invalid input data", e, flush=True)
        return make_response({"error": "Invalid input data", "success": False}, 400), 400

    try:
        print(f"Launching challenge for user ID {user_id} with template ID {challenge_template_id}", flush=True)
        accessible_networks: List[str] = launch_challenge_backend(challenge_template_id, user_id, MONITORING_VPN_INTERFACE, MONITORING_DMZ_INTERFACE)
    except Exception as e:
        print("Error launching challenge", e, flush=True)
        return make_response({"error": str(e), "success": False}, 500), 500

    return make_response({"message": "Challenge launched", "success": True, "entrypoints": accessible_networks}, 200), 200


@app.route('/stop-challenge', methods=['POST'])
def stop_challenge() -> Tuple[Dict[str, str | bool], int]:
    try:
        data: Dict[str, int] | None = request.json
        if not data:
            raise ValueError("No JSON data")
        user_id: int = int(data['user_id'])
    except Exception as e:
        print("Invalid input data", e, flush=True)
        return {"error": "Invalid input data", "success": False}, 500

    try:
        stop_challenge_backend(user_id)
    except Exception as e:
        print("Error stopping challenge", e, flush=True)
        return {"error": str(e), "success": False}, 500

    return {"message": "Challenge stopped", "success": True}, 200


@app.route('/import-machine-templates', methods=['POST'])
def import_machine_template() -> Tuple[Dict[str, str | bool], int]:
    db_conn: psycopg2.extensions.connection | None = None
    try:
        db_conn = get_db_connection()

        try:
            data: Dict[str, int] | None = request.json
            if not data:
                raise ValueError("No JSON data")
            challenge_template_id: int = int(data['challenge_template_id'])
        except Exception as e:
            print("Invalid input data", e, flush=True)
            return {"error": "Invalid input data", "success": False}, 500

        try:
            import_machine_template_backend(challenge_template_id, db_conn, ip_pool)
        except Exception as e:
            print("Error importing machine templates", e, flush=True)
            return {"error": str(e), "success": False}, 500

        return {"message": "Machine template imported", "success": True}, 200

    except Exception as e:
        print("Database connection error", e, flush=True)
        return {"error": "Database connection error", "success": False}, 500

    finally:
        if db_conn is not None:
            db_conn.close()


@app.route('/delete-machine-templates', methods=['POST'])
def delete_machine_templates() -> Tuple[Dict[str, str | bool], int]:
    db_conn: psycopg2.extensions.connection | None = None
    try:
        db_conn = get_db_connection()

        try:
            data: Dict[str, int] | None = request.json
            if not data:
                raise ValueError("No JSON data")
            challenge_id: int = int(data['challenge_id'])
        except Exception as e:
            print("Invalid input data", e, flush=True)
            return {"error": "Invalid input data", "success": False}, 500

        try:
            delete_machine_template_backend(challenge_id)
        except Exception as e:
            print("Error deleting machine templates", e, flush=True)
            return {"error": str(e), "success": False}, 500

        return {"message": "Machine templates deleted", "success": True}, 200

    except Exception as e:
        print("Database connection error", e, flush=True)
        return {"error": "Database connection error", "success": False}, 500

    finally:
        if db_conn is not None:
            db_conn.close()


@app.route('/get-user-config', methods=['POST'])
def get_user_config() -> Tuple[Dict[str, str | bool] | Response, int]:
    try:
        data: Dict[str, int] | None = request.json
        if not data:
            raise ValueError("No JSON data")
        user_id: int = int(data['user_id'])
    except Exception as e:
        print("Invalid input data", e, flush=True)
        return {"error": "Invalid input data", "success": False}, 500

    try:
        user_config_path: str = get_user_config_backend(user_id)
    except Exception as e:
        print("Error in getting user config", e, flush=True)
        return {"error": str(e), "success": False}, 500

    return send_file(user_config_path, as_attachment=True), 200


@app.route('/delete-user-config', methods=['POST'])
def delete_user_config() -> Tuple[Dict[str, str | bool], int]:
    data: Dict[str, int] | None = request.json
    if not data:
        return {"error": "No JSON data", "success": False}, 400
    user_id: int = int(data['user_id'])

    delete_user_config_backend(user_id)
    return {"message": "User config deleted", "success": True}, 200
    

app.run(host=BACKEND_HOST, port=int(BACKEND_PORT), ssl_context=(BACKEND_CERTIFICATE_FILE, BACKEND_CERTIFICATE_KEY_FILE))
