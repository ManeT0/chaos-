def run():
    return {"module": "dns_chaos", "status": "ok"}


def rollback():
    return {"module": "dns_chaos", "status": "rolled_back"}
