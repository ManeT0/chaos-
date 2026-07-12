import logging
from kubernetes import client, config

logger = logging.getLogger(__name__)

def _get_api():
    try:
        config.load_incluster_config()
    except Exception:
        config.load_kube_config()
    return client.CoreV1Api()

def run(namespace: str, label_selector: str, count: int = 1) -> dict:
    logger.info(f"Running pod_kill in {namespace} with selector {label_selector}, count {count}")
    api = _get_api()
    try:
        pods = api.list_namespaced_pod(namespace=namespace, label_selector=label_selector)
        if not pods.items:
            return {"status": "failed", "error": "No pods found matching selector"}
        
        killed_pods = []
        for pod in pods.items[:count]:
            api.delete_namespaced_pod(name=pod.metadata.name, namespace=namespace)
            killed_pods.append(pod.metadata.name)
            
        return {"status": "success", "killed_pods": killed_pods}
    except Exception as e:
        logger.error(f"Error in pod_kill: {e}")
        return {"status": "failed", "error": str(e)}

def cleanup() -> dict:
    logger.info("Cleaning up pod_kill")
    return {"status": "success", "message": "Nothing to clean up for pod_kill"}

def rollback() -> dict:
    return cleanup()
