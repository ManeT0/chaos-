import os
import time
import requests
import kopf
from datetime import datetime, timezone

ORCHESTRATOR_URL = os.getenv("ORCHESTRATOR_URL", "http://chaos-platform:8000")
ORCHESTRATOR_TOKEN = os.getenv("ORCHESTRATOR_TOKEN", "")

def get_headers():
    headers = {"Content-Type": "application/json"}
    if ORCHESTRATOR_TOKEN:
        headers["Authorization"] = f"Bearer {ORCHESTRATOR_TOKEN}"
    return headers

@kopf.on.create('chaos-platform.io', 'v1alpha1', 'chaosexperiments', retries=5, backoff=2.0)
def create_experiment(spec, name, namespace, logger, patch, **kwargs):
    logger.info(f"Creating experiment {name} in namespace {namespace}")
    patch.status['phase'] = 'Pending'
    patch.status['startedAt'] = datetime.now(timezone.utc).isoformat()
    
    experiment_name = spec.get('experiment')
    target = spec.get('target', namespace)
    target_type = spec.get('targetType', 'kubernetes')
    duration = spec.get('durationSeconds')
    dry_run = spec.get('dryRun', False)
    hypothesis_override = spec.get('hypothesisOverride')
    
    payload = {
        "name": experiment_name,
        "target": target,
        "duration_override": duration,
        "dry_run": dry_run,
        "hypothesis_override": hypothesis_override
    }
    
    try:
        response = requests.post(
            f"{ORCHESTRATOR_URL}/api/experiments/run", 
            json=payload, 
            headers=get_headers(),
            timeout=10
        )
        response.raise_for_status()
        result = response.json()
        
        patch.status['phase'] = 'Running'
        return {'api_response': result}
    except requests.exceptions.RequestException as e:
        logger.error(f"Failed to start experiment: {e}")
        patch.status['phase'] = 'Failed'
        patch.status['finishedAt'] = datetime.now(timezone.utc).isoformat()
        raise kopf.TemporaryError(f"API request failed: {e}", delay=5)

@kopf.on.update('chaos-platform.io', 'v1alpha1', 'chaosexperiments')
def update_experiment(spec, status, name, namespace, logger, patch, **kwargs):
    logger.info(f"Updating experiment {name} in namespace {namespace}")
    # In a real scenario, this might trigger an API call to update the running experiment.
    # We will just log it for now.
    pass

@kopf.on.delete('chaos-platform.io', 'v1alpha1', 'chaosexperiments', retries=3)
def delete_experiment(spec, name, namespace, logger, patch, **kwargs):
    logger.info(f"Deleting/Rolling back experiment {name} in namespace {namespace}")
    experiment_name = spec.get('experiment')
    target = spec.get('target', namespace)
    payload = {
        "name": experiment_name,
        "target": target
    }
    try:
        response = requests.post(
            f"{ORCHESTRATOR_URL}/api/experiments/rollback", 
            json=payload,
            headers=get_headers(),
            timeout=10
        )
        response.raise_for_status()
        patch.status['phase'] = 'Completed'
        patch.status['finishedAt'] = datetime.now(timezone.utc).isoformat()
        logger.info(f"Successfully rolled back experiment {name}")
    except requests.exceptions.RequestException as e:
        logger.error(f"Failed to rollback experiment: {e}")
        # We don't raise error to let Kopf delete the CR eventually, but log it.

@kopf.on.create('chaos-platform.io', 'v1alpha1', 'chaosschedules')
def create_schedule(spec, name, namespace, logger, patch, **kwargs):
    logger.info(f"Creating schedule {name} in namespace {namespace}")
    schedule = spec.get('schedule')
    template = spec.get('experimentTemplate')
    
    payload = {
        "name": name,
        "schedule": schedule,
        "template": template
    }
    
    try:
        response = requests.post(
            f"{ORCHESTRATOR_URL}/api/schedules", 
            json=payload,
            headers=get_headers(),
            timeout=10
        )
        response.raise_for_status()
        logger.info(f"Successfully created schedule {name}")
    except requests.exceptions.RequestException as e:
        logger.error(f"Failed to create schedule: {e}")
        raise kopf.TemporaryError(f"API request failed: {e}", delay=5)

