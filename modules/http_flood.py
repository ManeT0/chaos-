def run(url: str = "http://localhost", rps: int = 100):
    return {"module": "http_flood", "url": url, "rps": rps, "status": "ok"}


def rollback():
    return {"module": "http_flood", "status": "rolled_back"}
