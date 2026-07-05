def run(container: str | None = None):
    return {"module": "docker_kill", "container": container, "status": "ok"}


def rollback():
    return {"module": "docker_kill", "status": "rolled_back"}
