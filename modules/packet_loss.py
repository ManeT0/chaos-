def run(duration: int = 30, percentage: float = 10.0):
    return {
        "module": "packet_loss",
        "duration": duration,
        "percentage": percentage,
        "status": "ok",
    }


def rollback():
    return {"module": "packet_loss", "status": "rolled_back"}
