import os
from dotenv import load_dotenv
import requests
import subprocess
import fcntl
import base64
import time
from cloud_init_ip_pool import ip_pool
from typing import Dict, List, Any
from DatabaseClasses import (
    MachineTemplate,
    Machine,
    Network
)

load_dotenv()
node: str = os.getenv("PROXMOX_HOSTNAME", "pve")


def make_api_call(method: str, endpoint: str, data: Dict[str, Any] | None = None) -> Dict[str, Any]:
    """
    Make an API call to Proxmox.
    """
    proxmox_url: str | None = os.getenv("PROXMOX_URL")
    proxmox_api_token: str | None = os.getenv("PROXMOX_API_TOKEN")

    headers: Dict[str, str] = {}
    if data is not None:
        headers = {"Content-Type": "application/json"}

    if proxmox_api_token:
        headers["Authorization"] = f"PVEAPIToken={proxmox_api_token}"

    url: str = f"{proxmox_url}/{endpoint}"
    response: requests.Response = requests.request(method, url, headers=headers, json=data, verify="/etc/pve/pve-root-ca.pem")

    if response.status_code == 200:
        return response.json()
    else:
        raise Exception(f"Failed to make API call: {endpoint} - {response.status_code} - {response.text}")


def clone_vm_api_call(machine_template: MachineTemplate, machine: Machine) -> Dict[str, Any]:
    """
    Clone a virtual machine in Proxmox.
    """
    endpoint: str = f"api2/json/nodes/{node}/qemu/{machine_template.id}/clone"
    data: Dict[str, int | bool] = {
        "newid": machine.id,
        "full": False
    }
    return make_api_call("POST", endpoint, data)


def create_network_api_call(network: Network) -> Dict[str, Any]:
    """
    Create a network in Proxmox.
    """
    endpoint: str = f"api2/json/nodes/{node}/network"
    data: Dict[str, str | bool] = {
        "iface": network.host_device,
        "type": "bridge",
        "cidr": network.router_ip + "/" + network.subnet_mask,
        "autostart": True,
    }
    return make_api_call("POST", endpoint, data)


def reload_network_api_call() -> None:
    """
    Reload a network in Proxmox.
    """
    RELOAD_LOCK_FILE: str = "/var/lock/reload_network.lock"
    with open(RELOAD_LOCK_FILE, "w") as lock_file:
        try:
            fcntl.flock(lock_file, fcntl.LOCK_EX | fcntl.LOCK_NB) # type: ignore [attr-defined]

            endpoint: str = f"api2/json/nodes/{node}/network"
            data: Dict[str, Any] = {}
            make_api_call("PUT", endpoint, data)

            fcntl.flock(lock_file, fcntl.LOCK_UN) # type: ignore [attr-defined]
        except BlockingIOError:
            pass


def delete_vm_api_call(machine: MachineTemplate) -> Dict[str, Any]:
    """
    Delete a virtual machine in Proxmox.
    """
    endpoint: str = f"api2/json/nodes/{node}/qemu/{machine.id}"
    return make_api_call("DELETE", endpoint)


def delete_network_api_call(network: Network) -> Dict[str, Any]:
    """
    Delete a network in Proxmox.
    """
    endpoint: str = f"api2/json/nodes/{node}/network/{network.host_device}"
    return make_api_call("DELETE", endpoint)


def attach_networks_to_vm_api_call(machine: Machine) -> List[Dict[str, Any]]:
    """
    Attach networks to a virtual machine in Proxmox.
    """
    responses: List[Dict[str, Any]] = []

    for local_connection_id, connection in enumerate(machine.connections.values()):
        endpoint: str = f"api2/json/nodes/{node}/qemu/{machine.id}/config"
        data: Dict[str, str] = {
            f"net{local_connection_id}": f"model=e1000,"
                                         f"bridge={connection.network.host_device},"
                                         f"macaddr={connection.client_mac}"
        }

        responses.append(make_api_call("PUT", endpoint, data))

    return responses


def launch_vm_api_call(machine: Machine) -> Dict[str, Any]:
    """
    Launch a virtual machine in Proxmox.
    """
    endpoint: str = f"api2/json/nodes/{node}/qemu/{machine.id}/status/start"
    return make_api_call("POST", endpoint)


def stop_vm_api_call(machine: Machine) -> None:
    """
    Stop a virtual machine in Proxmox.
    """

    subprocess.run(["qm", "stop", str(machine.id), "--skiplock"], check=True, capture_output=True)


def shutdown_vm_api_call(machine: Machine) -> None:
    """
    Shutdown a virtual machine in Proxmox.
    """

    subprocess.run(["qm", "shutdown", str(machine.id)], check=True, capture_output=True)


def vm_is_stopped_api_call(machine: Machine) -> bool:
    """
    Check if a virtual machine is stopped in Proxmox.
    """

    out: subprocess.CompletedProcess[str] = subprocess.run(["qm", "status", str(machine.id)], check=True, capture_output=True, text=True)
    return "stopped" in out.stdout


def attach_cloud_init_drive(machine_template_id: int, storage: str = "local-lvm") -> Dict[str, Any]:
    """
    Attach a Cloud-Init disk to the VM so that cicustom will work.
    """
    endpoint: str = f"api2/json/nodes/{node}/qemu/{machine_template_id}/config"
    data: Dict[str, str] = {
        "ide2": f"{storage}:cloudinit"
    }
    return make_api_call("PUT", endpoint, data)


def detach_cloud_init_drive(machine_template_id: int) -> Dict[str, Any]:
    """
    Detach the Cloud-Init disk after configuration is done.
    """
    endpoint: str = f"api2/json/nodes/{node}/qemu/{machine_template_id}/config"
    data: Dict[str, str] = {
        "ide2": "none"
    }
    return make_api_call("PUT", endpoint, data)


def generate_prefixed_mac_address(vm_id: int, mac_index: str) -> str:
    """
    Generate a unique MAC address from a VM ID.
    Uses a locally administered prefix and encodes the VM ID in the last 4 bytes.
    Supports VM IDs up to 999,999,999.
    """
    if not (0 <= vm_id <= 999_999_999):
        raise ValueError("VM ID must be between 0 and 999,999,999")

    base_mac: str = mac_index  # locally administered prefix (first 2 bytes)

    vm_bytes: bytes = vm_id.to_bytes(4, 'big')
    mac_suffix: str = ":".join(f"{b:02x}" for b in vm_bytes)

    mac_address: str = f"{base_mac}:{mac_suffix}"
    return mac_address.lower()


def initial_configuration_api_call(machine_template: MachineTemplate, init_ip: str, cicustom_path: str) -> Dict[str, Any]:
    """
    Initial configuration of a virtual machine in Proxmox.
    """
    endpoint: str = f"api2/json/nodes/{node}/qemu/{machine_template.id}/config"
    data: Dict[str, Any] = {
        "memory": machine_template.ram,
        "cores": machine_template.cores,
        "sockets": 1,
        "cpu": "kvm64",
        "scsihw": "virtio-scsi-pci",
        "cicustom": f"user={cicustom_path}",
        "ipconfig30": f"ip={init_ip}/20,gw=10.32.0.1",
        "agent": 1
    }

    return make_api_call("PUT", endpoint, data)


def add_cloud_ipconfig(machine_template: MachineTemplate, init_ip: str, nic: int = 30, gw: str = "10.32.0.1") -> Dict[str, Any]:
    endpoint: str = f"api2/json/nodes/{node}/qemu/{machine_template.id}/config"
    data: Dict[str, str] = {
        f"ipconfig{nic}": f"ip={init_ip}/20,gw={gw}"
    }

    return make_api_call("PUT", endpoint, data)


def add_cloud_ipconfig_ipv6(machine_template: MachineTemplate, init_ip: str, nic: int = 31, gw: str = "fd12:3456:789a:1::1") -> Dict[str, Any]:
    endpoint: str = f"api2/json/nodes/{node}/qemu/{machine_template.id}/config"
    data: Dict[str, str] = {
        f"ipconfig{nic}": f"ip6={init_ip}/64,gw6={gw}"
    }

    return make_api_call("PUT", endpoint, data)


def set_cicustom_api_call(machine_id: int, user_custom_path: str, meta_custom_path: str) -> Dict[str, Any]:
    endpoint: str = f"api2/json/nodes/{node}/qemu/{machine_id}/config"
    data: Dict[str, str] = {
        "cicustom": f"user={user_custom_path},meta={meta_custom_path}"
    }

    return make_api_call("PUT", endpoint, data)


def add_network_device_api_call(machine_id: int, nic: str = "net30", bridge: str = "vmbr-cloud", model: str = "e1000", mac_index: str = "0A:00") -> Dict[str, Any]:
    """
    Add a network device to a virtual machine for internet access.
    """
    mac_address: str = generate_prefixed_mac_address(machine_id, mac_index)
    endpoint: str = f"api2/json/nodes/{node}/qemu/{machine_id}/config"
    data: Dict[str, str] = {
        nic: f"model={model},bridge={bridge},macaddr={mac_address}"
    }
    return make_api_call("PUT", endpoint, data)


def detach_network_device_api_call(vmid: int, nic: str = "net30") -> Dict[str, Any]:
    """
    Remove a network device from a VM.
    """
    endpoint: str = f"api2/json/nodes/{node}/qemu/{vmid}/config"
    data: Dict[str, str] = {
        "delete": nic
    }
    return make_api_call("PUT", endpoint, data)


def convert_vm_to_template_api_call(machine_template_id: int) -> Dict[str, Any]:
    """
    Convert a virtual machine to a template in Proxmox.
    """
    endpoint: str = f"api2/json/nodes/{node}/qemu/{machine_template_id}/template"
    return make_api_call("POST", endpoint)


def vm_exists_api_call(machine: Machine) -> bool:
    """
    Check if a virtual machine exists in Proxmox.
    """
    endpoint: str = f"api2/json/nodes/{node}/qemu/{machine.id}/status/current"
    try:
        make_api_call("GET", endpoint)
        return True
    except Exception:
        return False


def vm_is_template_api_call(machine_template: MachineTemplate) -> bool:
    """
    Check if a virtual machine is a template in Proxmox.
    """
    endpoint: str = f"api2/json/nodes/{node}/qemu/{machine_template.id}/config"
    response: Dict[str, Any] = make_api_call("GET", endpoint)

    return response["data"]["template"] == 0 if "template" in response["data"] else False


def get_sockets_api_call(machine_template: MachineTemplate) -> int:
    """
    Get the number of sockets for a virtual machine in Proxmox.
    """
    endpoint: str = f"api2/json/nodes/{node}/qemu/{machine_template.id}/config"
    response: Dict[str, Any] = make_api_call("GET", endpoint)

    return response["data"]["sockets"] if "sockets" in response["data"] else 1


def get_memory_api_call(machine_template: MachineTemplate) -> int:
    """
    Get the memory size for a virtual machine in Proxmox.
    """
    endpoint: str = f"api2/json/nodes/{node}/qemu/{machine_template.id}/config"
    response: Dict[str, Any] = make_api_call("GET", endpoint)

    return response["data"]["memory"]


def network_device_exists_api_call(network: Network) -> bool:
    """
    Check if a network device exists in Proxmox.
    """
    endpoint: str = f"api2/json/nodes/{node}/network/{network.host_device}"
    try:
        make_api_call("GET", endpoint)
        return True
    except Exception:
        return False
