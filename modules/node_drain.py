import logging
from kubernetes import client, config

logger = logging.getLogger(__name__)

_CORDONED_NODES = []

def _get_core_api():
    try:
        config.load_incluster_config()
    except Exception:
        config.load_kube_config()
    return client.CoreV1Api()

def _get_policy_api():
    try:
        config.load_incluster_config()
    except Exception:
        config.load_kube_config()
    return client.PolicyV1Api()

def run(node_name: str, evict_pods: bool = True) -> dict:
    logger.info(f"Running node_drain on {node_name}")
    core_api = _get_core_api()
    policy_api = _get_policy_api()
    
    try:
        # Cordon the node
        body = {
            "spec": {
                "unschedulable": True
            }
        }
        core_api.patch_node(node_name, body)
        if node_name not in _CORDONED_NODES:
            _CORDONED_NODES.append(node_name)
        
        evicted = []
        if evict_pods:
            # Evict pods
            pods = core_api.list_pod_for_all_namespaces(field_selector=f"spec.nodeName={node_name}")
            for pod in pods.items:
                eviction = client.V1Eviction(
                    metadata=client.V1ObjectMeta(name=pod.metadata.name, namespace=pod.metadata.namespace)
                )
                try:
                    policy_api.create_namespaced_pod_eviction(name=pod.metadata.name, namespace=pod.metadata.namespace, body=eviction)
                    evicted.append(pod.metadata.name)
                except Exception as e:
                    logger.warning(f"Failed to evict {pod.metadata.name}: {e}")
                    
        return {"status": "success", "node": node_name, "evicted_pods": evicted}
    except Exception as e:
        logger.error(f"Error in node_drain: {e}")
        return {"status": "failed", "error": str(e)}

def cleanup() -> dict:
    logger.info("Cleaning up node_drain")
    core_api = _get_core_api()
    results = []
    
    for node_name in list(_CORDONED_NODES):
        try:
            body = {
                "spec": {
                    "unschedulable": False
                }
            }
            core_api.patch_node(node_name, body)
            _CORDONED_NODES.remove(node_name)
            results.append({"node": node_name, "status": "uncordoned"})
        except Exception as e:
            logger.error(f"Failed to uncordon {node_name}: {e}")
            results.append({"node": node_name, "error": str(e)})
            
    return {"status": "success", "results": results}

def rollback() -> dict:
    return cleanup()
