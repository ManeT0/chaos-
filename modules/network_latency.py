def run(duration: int = 30):
    return {"module": "network_latency", "duration": duration, "status": "ok"}


def rollback():
    return {"module": "network_latency", "status": "rolled_back"}
