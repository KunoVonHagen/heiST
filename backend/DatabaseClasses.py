import dataclasses

from subnet_calculations import nth_machine_ip
from typing import Dict, List, Tuple

class ChallengeTemplate:
    def __init__(self, challenge_template_id: int) -> None:
        self.id: int = challenge_template_id
        self.machine_templates: Dict[int, MachineTemplate] = {} # machine_template.id -> machine_template
        self.network_templates: Dict[int, "NetworkTemplate"] = {} # network_template.id -> network_template
        self.connection_templates: Dict[Tuple[int, int], "ConnectionTemplate"] = {} # (machine_template.id, network_template.id) -> connection_template
        self.domain_templates: Dict[Tuple[int, str], "DomainTemplate"] = {} # (machine_template.id, domain) -> domain_template
        self.challenge_subnet: str = ""
        self.flags: List[Flag] = []

    def add_machine_template(self, machine_template: "MachineTemplate") -> None:
        self.machine_templates[machine_template.id] = machine_template

    def add_network_template(self, network_template: "NetworkTemplate") -> None:
        self.network_templates[network_template.id] = network_template

    def add_connection_template(self, connection_template: "ConnectionTemplate") -> None:
        self.connection_templates[(connection_template.machine_template.id, connection_template.network_template.id)] \
            = connection_template

    def add_domain_template(self, domain_template: "DomainTemplate") -> None:
        self.domain_templates[(domain_template.machine_template.id, domain_template.domain)] = domain_template

    def set_challenge_subnet(self, challenge_subnet: str) -> None:
        self.challenge_subnet = challenge_subnet


class MachineTemplate:
    def __init__(self, machine_template_id: int, challenge_template: ChallengeTemplate) -> None:
        self.id: int = machine_template_id
        self.challenge_template: ChallengeTemplate = challenge_template
        self.connected_networks: Dict[int, "NetworkTemplate"] = {} # network_template.id -> network_template
        self.domain_templates: Dict[Tuple[int, str], "DomainTemplate"] = {} # domain_template.id -> domain_template
        self.child: "Machine | None" = None
        self.disk_file_path: str = ""
        self.cores: int = 1
        self.ram: int = 1024 # MiB

    def add_connected_network(self, network_template: "NetworkTemplate") -> None:
        self.connected_networks[network_template.id] = network_template

    def set_child(self, child: "Machine") -> None:
        self.child = child

    def add_domain_template(self, domain_template: "DomainTemplate") -> None:
        self.domain_templates[(domain_template.machine_template.id, domain_template.domain)] = domain_template

    def set_disk_file_path(self, disk_file_path: str) -> None:
        self.disk_file_path = disk_file_path

    def set_cores(self, cores: int) -> None:
        self.cores = cores

    def set_ram(self, ram: int) -> None:
        self.ram = ram


class NetworkTemplate:
    def __init__(self, network_template_id: int, accessible: bool) -> None:
        self.id: int = network_template_id
        self.accessible: bool = accessible
        self.connected_machines: Dict[int, MachineTemplate] = {} # machine_template.id -> machine_template
        self.is_dmz: bool = False

    def add_connected_machine(self, machine: MachineTemplate) -> None:
        self.connected_machines[machine.id] = machine

    def set_is_dmz(self, is_dmz: bool) -> None:
        self.is_dmz = is_dmz


class ConnectionTemplate:
    def __init__(self, machine_template: MachineTemplate, network_template: NetworkTemplate) -> None:
        self.machine_template: MachineTemplate = machine_template
        self.network_template: NetworkTemplate = network_template

    def set_machine_template(self, machine_template: MachineTemplate) -> None:
        self.machine_template = machine_template

    def set_network_template(self, network_template: NetworkTemplate) -> None:
        self.network_template = network_template


class DomainTemplate:
    def __init__(self, machine_template: MachineTemplate, domain: str) -> None:
        self.machine_template: MachineTemplate = machine_template
        self.domain: str = domain


class Challenge:
    def __init__(self, challenge_id: int, template: ChallengeTemplate, subnet: str) -> None:
        self.id: int = challenge_id
        self.template: ChallengeTemplate = template
        self.subnet: str = subnet
        self.subnet_ip: str = subnet[:-3]
        self.subnet_mask: str = subnet[-2:]

        self.machines: Dict[int, Machine] = {} # machine.id -> machine
        self.networks: Dict[int, Network] = {} # network.id -> network
        self.connections: Dict[Tuple[int, int], Connection] = {} # (machine.id, network.id) -> connection
        self.domains: Dict[Tuple[int, str], "Domain"] = {} # (machine.id, domain(str)) -> domain(object)
        self.challenge_subnet: str = ""

    def add_machine(self, machine: "Machine") -> None:
        self.machines[machine.id] = machine

    def add_network(self, network: "Network") -> None:
        self.networks[network.id] = network

    def add_connection(self, connection: "Connection") -> None:
        self.connections[(connection.machine.id, connection.network.id)] = connection

    def add_domain(self, domain: "Domain") -> None:
        self.domains[(domain.machine.id, domain.domain)] = domain

    def set_challenge_subnet(self, challenge_subnet: str) -> None:
        self.challenge_subnet = challenge_subnet


class Machine:
    def __init__(self, machine_id: int, template: MachineTemplate, challenge: Challenge) -> None:
        self.id: int = machine_id
        self.template: MachineTemplate = template
        self.challenge: Challenge = challenge

        self.connections: Dict[int, Connection] = {} # network.id -> connection
        self.domains: List[str] = []

    def add_connection(self, connection: "Connection") -> None:
        self.connections[connection.network.id] = connection

    def add_domain(self, domain: "Domain") -> None:
        self.domains.append(domain.domain)


class Network:
    def __init__(self, network_id: int, template: NetworkTemplate, subnet: str, host_device: str, accessible: bool) -> None:
        self.id: int = network_id
        self.template: NetworkTemplate = template
        self.subnet: str = subnet
        self.host_device: str = host_device
        self.accessible: bool = accessible

        self.subnet_ip: str
        self.subnet_mask: str
        self.subnet_ip, self.subnet_mask = self.subnet.split("/")
        self.connections: Dict[int, Connection] = {} # machine.id -> connection

        self.router_ip: str = nth_machine_ip(self.subnet_ip, 1, True)
        self.available_start_ip: str = nth_machine_ip(self.subnet_ip, 2)
        self.available_end_ip: str = nth_machine_ip(self.subnet_ip, 2**4 - 2)

        self.is_dmz: bool = False

    def add_connection(self, connection: "Connection") -> None:
        self.connections[connection.machine.id] = connection

    def set_is_dmz(self, is_dmz: bool) -> None:
        self.is_dmz = is_dmz


class Connection:
    def __init__(self, machine: Machine, network: Network, client_mac: str, client_ip: str) -> None:
        self.machine: Machine = machine
        self.network: Network = network
        self.client_mac: str = client_mac
        self.client_ip: str = client_ip


class Domain:
    def __init__(self, machine: Machine, domain: str) -> None:
        self.machine: Machine = machine
        self.domain: str = domain


class ChallengeSubnet:
    def __init__(self, subnet: str) -> None:
        self.subnet: str = subnet


@dataclasses.dataclass
class Flag:
    id: int
    secret: str
    description: str
    points: int
    order_index: int
    user_specific: bool
    machine_template: MachineTemplate


@dataclasses.dataclass
class MachineFlagEntry:
    path: str
    flag: str

@dataclasses.dataclass
class IPPoolManagerStatus:
    total_ips: int
    available_ips: int
    allocated_ips: int
    allocated_vms: List[int]
