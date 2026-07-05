def run(duration: int = 30):
    return {"module": "memory_stress", "duration": duration, "status": "ok"}


def rollback():
    return {"module": "memory_stress", "status": "rolled_back"}
