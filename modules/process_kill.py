def run(pid: int | None = None):
    return {"module": "process_kill", "pid": pid, "status": "ok"}


def rollback():
    return {"module": "process_kill", "status": "rolled_back"}
