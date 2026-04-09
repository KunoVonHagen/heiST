import threading
import ipaddress
import time
from typing import Dict, Set

from backend.DatabaseClasses import IPPoolManagerStatus


class IPPoolManager:
    _instance: "IPPoolManager | None" = None
    _instance_lock: threading.Lock = threading.Lock()

    def __new__(cls) -> "IPPoolManager":
        with cls._instance_lock:
            if cls._instance is None:
                cls._instance = super().__new__(cls)
                cls._instance._initialize()
            return cls._instance

    def _initialize(self) -> None:
        self.pool_lock: threading.RLock = threading.RLock()
        self.wait_condition: threading.Condition[threading.RLock] = threading.Condition(self.pool_lock)

        self.network: ipaddress.IPv4Network = ipaddress.ip_network('10.32.0.0/20')
        hosts: list[str] = [str(ip) for ip in self.network.hosts()]
        self.available_ips: Set[str] = set(hosts)
        self.allocated_ips: Dict[int, str] = {} # machine_id -> ip_address
        self.allocated_ip_set: Set[str] = set()

        self.total_ips: int = len(hosts)

    def allocate_ip(self, vm_id: int, timeout: float = 300.0, reuse_existing: bool = True) -> str:
        """
        Allocate an IP for vm_id. If reuse_existing is True and vm_id already has an IP,
        return it instead of allocating a new one.
        Raises TimeoutError if no IP available within timeout.
        """
        start: float = time.time()
        with self.wait_condition:
            if reuse_existing:
                existing: str | None = self.allocated_ips.get(vm_id)
                if existing:
                    return existing

            while True:
                if self.available_ips:
                    ip: str = self.available_ips.pop()
                    self.allocated_ips[vm_id] = ip
                    self.allocated_ip_set.add(ip)
                    self.wait_condition.notify_all()
                    return ip

                remaining: float = timeout - (time.time() - start)
                if remaining <= 0:
                    raise TimeoutError(f"Could not allocate IP within {timeout} seconds")
                self.wait_condition.wait(remaining)

    def release_ip(self, vm_id: int) -> bool:
        """Release IP assigned to vm_id and notify waiting threads."""
        with self.wait_condition:
            ip: str | None = self.allocated_ips.pop(vm_id, None)
            if not ip:
                return False
            # return to pool
            if ip not in self.available_ips:
                self.available_ips.add(ip)
            self.allocated_ip_set.discard(ip)
            self.wait_condition.notify_all()
            return True

    def get_allocated_ip(self, vm_id: int) -> str | None:
        with self.pool_lock:
            return self.allocated_ips.get(vm_id)

    def get_pool_status(self) -> IPPoolManagerStatus:
        with self.pool_lock:
            return IPPoolManagerStatus(
                total_ips=self.total_ips,
                available_ips=len(self.available_ips),
                allocated_ips=len(self.allocated_ips),
                allocated_vms=list(self.allocated_ips.keys())
            )

    def is_ip_allocated(self, ip: str) -> bool:
        with self.pool_lock:
            return ip in self.allocated_ip_set

    def cleanup(self) -> None:
        with self.wait_condition:
            self.available_ips.update(self.allocated_ips.values())
            self.allocated_ips.clear()
            self.allocated_ip_set.clear()
            self.wait_condition.notify_all()

# Singleton
ip_pool: IPPoolManager = IPPoolManager()
