from kubernetes import client, config
from kubernetes.client.rest import ApiException

GROUP = "chaos-mesh.org"
VERSION = "v1alpha1"
PLURAL = "networkchaos"

def get_k8s_client():
    try:
        config.load_incluster_config()
    except config.ConfigException:
        config.load_kube_config()
    return client.CustomObjectsApi()

def run(duration: int = 30, namespace: str = "default", selector: dict = None, latency_ms: str = "10ms", name: str = "network-delay", **kwargs) -> dict:
    if selector is None:
        selector = {"app": "demo"}
        
    api = get_k8s_client()
    cr = {
        "apiVersion": f"{GROUP}/{VERSION}",
        "kind": "NetworkChaos",
        "metadata": {
            "name": name,
            "namespace": namespace
        },
        "spec": {
            "action": "delay",
            "mode": "all",
            "selector": {
                "labelSelectors": selector
            },
            "delay": {
                "latency": latency_ms,
                "correlation": "0",
                "jitter": "0ms"
            },
            "duration": f"{duration}s"
        }
    }
    
    try:
        response = api.create_namespaced_custom_object(
            group=GROUP,
            version=VERSION,
            namespace=namespace,
            plural=PLURAL,
            body=cr
        )
        return {"status": "success", "message": f"NetworkChaos {name} created", "cr": response}
    except ApiException as e:
        return {"status": "error", "error": str(e)}

def rollback(namespace: str = "default", name: str = "network-delay", **kwargs) -> dict:
    api = get_k8s_client()
    try:
        api.delete_namespaced_custom_object(
            group=GROUP,
            version=VERSION,
            namespace=namespace,
            plural=PLURAL,
            name=name
        )
        return {"status": "success", "message": f"NetworkChaos {name} deleted"}
    except ApiException as e:
        if e.status == 404:
            return {"status": "success", "message": "Already deleted"}
        return {"status": "error", "error": str(e)}
