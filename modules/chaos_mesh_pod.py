from kubernetes import client, config
from kubernetes.client.rest import ApiException

GROUP = "chaos-mesh.org"
VERSION = "v1alpha1"
PLURAL = "podchaos"

def get_k8s_client():
    try:
        config.load_incluster_config()
    except config.ConfigException:
        config.load_kube_config()
    return client.CustomObjectsApi()

def run(duration: int = 30, namespace: str = "default", selector: dict = None, action: str = "pod-kill", name: str = "pod-chaos", **kwargs) -> dict:
    if selector is None:
        selector = {"app": "demo"}
        
    api = get_k8s_client()
    cr = {
        "apiVersion": f"{GROUP}/{VERSION}",
        "kind": "PodChaos",
        "metadata": {
            "name": name,
            "namespace": namespace
        },
        "spec": {
            "action": action, # pod-kill, pod-failure, container-kill
            "mode": "one",
            "selector": {
                "labelSelectors": selector
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
        return {"status": "success", "message": f"PodChaos {name} created", "cr": response}
    except ApiException as e:
        return {"status": "error", "error": str(e)}

def rollback(namespace: str = "default", name: str = "pod-chaos", **kwargs) -> dict:
    api = get_k8s_client()
    try:
        api.delete_namespaced_custom_object(
            group=GROUP,
            version=VERSION,
            namespace=namespace,
            plural=PLURAL,
            name=name
        )
        return {"status": "success", "message": f"PodChaos {name} deleted"}
    except ApiException as e:
        if e.status == 404:
            return {"status": "success", "message": "Already deleted"}
        return {"status": "error", "error": str(e)}
