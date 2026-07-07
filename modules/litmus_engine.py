from kubernetes import client, config
from kubernetes.client.rest import ApiException

GROUP = "litmuschaos.io"
VERSION = "v1alpha1"
PLURAL = "chaosengines"

def get_k8s_client():
    try:
        config.load_incluster_config()
    except config.ConfigException:
        config.load_kube_config()
    return client.CustomObjectsApi()

def run(duration: int = 30, namespace: str = "default", app_label: str = "app=demo", experiment_name: str = "pod-delete", name: str = "litmus-engine", **kwargs) -> dict:
    api = get_k8s_client()
    cr = {
        "apiVersion": f"{GROUP}/{VERSION}",
        "kind": "ChaosEngine",
        "metadata": {
            "name": name,
            "namespace": namespace
        },
        "spec": {
            "appinfo": {
                "appns": namespace,
                "applabel": app_label,
                "appkind": "deployment"
            },
            "chaosServiceAccount": "litmus-admin",
            "engineState": "active",
            "experiments": [
                {
                    "name": experiment_name,
                    "spec": {
                        "components": {
                            "env": [
                                {
                                    "name": "TOTAL_CHAOS_DURATION",
                                    "value": str(duration)
                                }
                            ]
                        }
                    }
                }
            ]
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
        return {"status": "success", "message": f"ChaosEngine {name} created", "cr": response}
    except ApiException as e:
        return {"status": "error", "error": str(e)}

def rollback(namespace: str = "default", name: str = "litmus-engine", **kwargs) -> dict:
    api = get_k8s_client()
    try:
        api.delete_namespaced_custom_object(
            group=GROUP,
            version=VERSION,
            namespace=namespace,
            plural=PLURAL,
            name=name
        )
        return {"status": "success", "message": f"ChaosEngine {name} deleted"}
    except ApiException as e:
        if e.status == 404:
            return {"status": "success", "message": "Already deleted"}
        return {"status": "error", "error": str(e)}
