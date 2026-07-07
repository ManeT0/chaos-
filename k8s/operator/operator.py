import os
import requests
import kopf

ORCHESTRATOR_URL = os.getenv("ORCHESTRATOR_URL", "http://chaos-platform:8000")

@kopf.on.create('chaos-platform.io', 'v1alpha1', 'chaosexperiments')
def create_fn(spec, name, namespace, logger, **kwargs):
    logger.info(f"Creating experiment {name} in namespace {namespace}")
    
    experiment_name = spec.get('experiment')
    target = spec.get('target', namespace)
    target_type = spec.get('targetType', 'kubernetes')
    duration = spec.get('durationSeconds')
    dry_run = spec.get('dryRun')
    
    payload = {
        "name": experiment_name,
        "target": target,
        "duration_override": duration,
        "dry_run": dry_run
    }
    
    try:
        # Note: The platform's backend expects a POST to /api/experiments/run
        response = requests.post(f"{ORCHESTRATOR_URL}/api/experiments/run", json=payload)
        response.raise_for_status()
        result = response.json()
        
        return {
            'phase': 'Running',
            'api_response': result
        }
    except Exception as e:
        logger.error(f"Failed to start experiment: {e}")
        return {
            'phase': 'Failed',
            'error': str(e)
        }

@kopf.on.delete('chaos-platform.io', 'v1alpha1', 'chaosexperiments')
def delete_fn(spec, name, namespace, logger, **kwargs):
    logger.info(f"Deleting/Rolling back experiment {name} in namespace {namespace}")
    # Call orchestrator to rollback, if rollback endpoint is implemented, 
    # or just let Kopf clean up the CR. 
    # For now, orchestrator runs for a duration and stops.
    pass
