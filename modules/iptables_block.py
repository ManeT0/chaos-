def run(port: int = 80):
    return {"module": "iptables_block", "port": port, "status": "ok"}


def rollback():
    return {"module": "iptables_block", "status": "rolled_back"}
