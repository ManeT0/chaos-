import logging
from kubernetes import client, config

logger = logging.getLogger(__name__)

_CREATED_POLICIES = []

def _get_api():
    try:
        config.load_incluster_config()
    except Exception:
        config.load_kube_config()
    return client.NetworkingV1Api()

def run(namespace: str, target_labels: dict, isolate_from_labels: dict = None) -> dict:
    logger.info(f"Running region_failure in {namespace}")
    api = _get_api()
    
    policy_name = f"region-isolation-{namespace}"
    
    # A simple NetworkPolicy to block incoming traffic to the region
    policy = client.V1NetworkPolicy(
        metadata=client.V1ObjectMeta(name=policy_name, namespace=namespace),
        spec=client.V1NetworkPolicySpec(
            pod_selector=client.V1LabelSelector(match_labels=target_labels),
            policy_types=["Ingress", "Egress"],
            ingress=[
                client.V1NetworkPolicyIngressRule(
                    from_=[] # Deny all
                )
            ]
        )
    )
    
    try:
        api.create_namespaced_network_policy(namespace=namespace, body=policy)
        _CREATED_POLICIES.append((namespace, policy_name))
        return {"status": "success", "policy": policy_name}
    except Exception as e:
        logger.error(f"Error in region_failure: {e}")
        return {"status": "failed", "error": str(e)}

def cleanup() -> dict:
    logger.info("Cleaning up region_failure")
    api = _get_api()
    results = []
    
    for ns, name in list(_CREATED_POLICIES):
        try:
            api.delete_namespaced_network_policy(name=name, namespace=ns)
            _CREATED_POLICIES.remove((ns, name))
            results.append({"policy": name, "status": "deleted"})
        except Exception as e:
            logger.error(f"Failed to delete policy {name} in {ns}: {e}")
            results.append({"policy": name, "error": str(e)})
            
    return {"status": "success", "results": results}

def rollback() -> dict:
    return cleanup()
