import subprocess
import os
from dotenv import load_dotenv
import fcntl
import time

from .delete_user_config import delete_user_config
from .get_db_connection import db_connection_context

load_dotenv()

LOCK_FILE: str = "/var/lock/easy_rsa.lock"


def get_user_config(user_id: int) -> str:
    """
    Create a user configuration for a challenge.
    Raises ValueError if user not found, FileNotFoundError if certificates missing, TimeoutError if lock acquisition fails.
    """

    with db_connection_context() as db_conn:
        client_config_dir: str = "/etc/openvpn/client-configs"
        client_config_path: str = os.path.join(client_config_dir, f"{user_id}.ovpn")
        if os.path.exists(client_config_path):
            return client_config_path

        with db_conn.cursor() as cursor:
            cursor.execute("SELECT vpn_static_ip FROM users WHERE id = %s", (user_id,))
            result: tuple[str] | None = cursor.fetchone()
            if result is None:
                raise ValueError(f"User with ID {user_id} not found.")

        static_ip: str = result[0]

        try:
            easy_rsa_dir: str = "/etc/openvpn/easy-rsa"
            easy_rsa_binary: str = os.path.join(easy_rsa_dir, "easyrsa")

            ccd_dir: str = "/etc/openvpn/ccd"
            ccd_file: str = os.path.join(ccd_dir, str(user_id))

            vpn_server_ip: str | None = os.getenv("VPN_SERVER_IP")

            # Ensure necessary directories exist
            os.makedirs(ccd_dir, exist_ok=True)
            os.makedirs(client_config_dir, exist_ok=True)

            # Generate client certificate and key
            env: dict[str, str] = os.environ.copy()
            env["EASYRSA"] = "/etc/openvpn/easy-rsa"
            env["EASYRSA_PKI"] = "/etc/openvpn/easy-rsa/pki"
            env['EASYRSA_BATCH'] = '1'

            timeout: int = 30
            start: float = time.time()
            with open(LOCK_FILE, 'w') as lock_file:
                while True:
                    try:
                        fcntl.flock(lock_file, fcntl.LOCK_EX | fcntl.LOCK_NB) # type: ignore [attr-defined]
                        break  # acquired
                    except BlockingIOError:
                        if time.time() - start > timeout:
                            raise TimeoutError(f"Could not acquire lock within {timeout}s")
                        time.sleep(0.1)  # back off a bit

                try:
                    subprocess.run(
                        [easy_rsa_binary, "--batch", "build-client-full", str(user_id), "nopass"],
                        cwd=easy_rsa_dir, check=True, env=env, capture_output=True
                    )
                finally:
                    fcntl.flock(lock_file, fcntl.LOCK_UN) # type: ignore [attr-defined]

            # Assign static IP to the client
            with open(ccd_file, 'w') as f:
                f.write(f"ifconfig-push {static_ip} 255.255.255.0\n")

            ca_crt_path: str = os.path.join(easy_rsa_dir, "pki", "ca.crt")
            if not os.path.exists(ca_crt_path):
                raise FileNotFoundError(f"CA certificate not found at {ca_crt_path}")

            cert_path: str = os.path.join(easy_rsa_dir, "pki", "issued", f"{user_id}.crt")
            if not os.path.exists(cert_path):
                raise FileNotFoundError(f"Client certificate not found at {cert_path}")

            key_path: str = os.path.join(easy_rsa_dir, "pki", "private", f"{user_id}.key")
            if not os.path.exists(key_path):
                raise FileNotFoundError(f"Client key not found at {key_path}")

            ta_key_path: str = os.path.join(easy_rsa_dir, "ta.key")
            if not os.path.exists(ta_key_path):
                raise FileNotFoundError(f"TLS auth key not found at {ta_key_path}")

            # Read the contents of the keys
            ca_crt: str = open(ca_crt_path).read()
            cert: str = open(cert_path).read()
            key: str = open(key_path).read()
            ta_key: str = open(ta_key_path).read()

            client_config: str = f"""client
    dev tun
    proto udp
    remote {vpn_server_ip} 1194
    resolv-retry infinite
    nobind
    persist-key
    persist-tun
    verb 3
    explicit-exit-notify 2
    key-direction 1
    
    tun-mtu 1338
    mssfix 1290
    
    <ca>
    {ca_crt}
    </ca>
    <cert>
    {cert}
    </cert>
    <key>
    {key}
    </key>
    <tls-auth>
    {ta_key}
    </tls-auth>
    """

            with open(client_config_path, 'w') as config:
                config.write(client_config)

            return client_config_path

        except Exception as e:
            # Clean up if an error occurs
            delete_user_config(user_id)
            raise e
