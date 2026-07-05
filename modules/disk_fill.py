def run(size_mb: int = 5120):
    return {"module": "disk_fill", "size_mb": size_mb, "status": "ok"}


def rollback():
    return {"module": "disk_fill", "status": "rolled_back"}
