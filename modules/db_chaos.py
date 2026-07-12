import logging
import subprocess
import threading
import socket
import time

logger = logging.getLogger(__name__)

_CLEANUP_TASKS = []

def run(chaos_type: str, port: int, duration: int = 60, connections: int = 100, target_host: str = "127.0.0.1") -> dict:
    logger.info(f"Running db_chaos: {chaos_type} on port {port}")
    try:
        if chaos_type == "connection_drop":
            subprocess.run(["iptables", "-A", "INPUT", "-p", "tcp", "--dport", str(port), "-j", "DROP"], check=True)
            _CLEANUP_TASKS.append(("iptables", "-D", "INPUT", "-p", "tcp", "--dport", str(port), "-j", "DROP"))
            return {"status": "success", "action": "iptables_drop"}
            
        elif chaos_type == "slow_queries":
            subprocess.run(["tc", "qdisc", "add", "dev", "eth0", "root", "handle", "1:", "prio"], check=True)
            subprocess.run(["tc", "qdisc", "add", "dev", "eth0", "parent", "1:3", "handle", "30:", "netem", "delay", "100ms"], check=True)
            subprocess.run(["tc", "filter", "add", "dev", "eth0", "protocol", "ip", "parent", "1:0", "prio", "3", "u32", "match", "ip", "dport", str(port), "0xffff", "flowid", "1:3"], check=True)
            
            _CLEANUP_TASKS.append(("tc", "qdisc", "del", "dev", "eth0", "root"))
            return {"status": "success", "action": "tc_delay"}
            
        elif chaos_type == "connection_pool_exhaust":
            def exhaust_task():
                sockets = []
                for _ in range(connections):
                    try:
                        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                        s.connect((target_host, port))
                        sockets.append(s)
                    except Exception:
                        pass
                time.sleep(duration)
                for s in sockets:
                    try:
                        s.close()
                    except:
                        pass

            t = threading.Thread(target=exhaust_task)
            t.daemon = True
            t.start()
            return {"status": "success", "action": "exhaust_pool"}
        else:
            return {"status": "failed", "error": f"Unknown chaos_type: {chaos_type}"}
    except Exception as e:
        logger.error(f"Error in db_chaos: {e}")
        return {"status": "failed", "error": str(e)}

def cleanup() -> dict:
    logger.info("Cleaning up db_chaos")
    results = []
    
    for task in list(_CLEANUP_TASKS):
        try:
            subprocess.run(list(task), check=True)
            _CLEANUP_TASKS.remove(task)
            results.append({"task": task, "status": "cleaned"})
        except Exception as e:
            logger.error(f"Failed to run cleanup task {task}: {e}")
            results.append({"task": task, "error": str(e)})
            
    return {"status": "success", "results": results}

def rollback() -> dict:
    return cleanup()
