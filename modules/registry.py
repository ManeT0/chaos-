from dataclasses import dataclass
from typing import Callable

from modules import (
    cpu_stress,
    disk_fill,
    dns_chaos,
    docker_kill,
    http_flood,
    iptables_block,
    memory_stress,
    network_latency,
    packet_loss,
    process_kill,
)


@dataclass(frozen=True)
class ChaosModule:
    run: Callable[..., dict]
    rollback: Callable[[], dict] | None = None


MODULES: dict[str, ChaosModule] = {
    "cpu_stress": ChaosModule(run=cpu_stress.run, rollback=cpu_stress.rollback),
    "disk_fill": ChaosModule(run=disk_fill.run, rollback=disk_fill.rollback),
    "memory_stress": ChaosModule(run=memory_stress.run, rollback=memory_stress.rollback),
    "network_latency": ChaosModule(run=network_latency.run, rollback=network_latency.rollback),
    "packet_loss": ChaosModule(run=packet_loss.run, rollback=packet_loss.rollback),
    "dns_chaos": ChaosModule(run=dns_chaos.run, rollback=dns_chaos.rollback),
    "process_kill": ChaosModule(run=process_kill.run, rollback=process_kill.rollback),
    "docker_kill": ChaosModule(run=docker_kill.run, rollback=docker_kill.rollback),
    "http_flood": ChaosModule(run=http_flood.run, rollback=http_flood.rollback),
    "iptables_block": ChaosModule(run=iptables_block.run, rollback=iptables_block.rollback),
}


def get_module(name: str) -> ChaosModule | None:
    return MODULES.get(name)
