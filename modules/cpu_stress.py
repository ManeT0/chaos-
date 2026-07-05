def run(duration: int = 30):
    return {"module": "cpu_stress", "duration": duration, "status": "ok"}


def rollback():
    return {"module": "cpu_stress", "status": "rolled_back"}
