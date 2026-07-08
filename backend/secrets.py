import os
import re
import requests

from typing import Any

# Regex to match ${VAR_NAME} or ${VAR_NAME:default}
SECRET_PATTERN = re.compile(r"\$\{([^}]+)\}")

def resolve_secrets(data: Any) -> Any:
    """
    Recursively traverse dicts/lists and replace ${VAR} with environment variables
    or Vault secrets.
    """
    if isinstance(data, dict):
        return {k: resolve_secrets(v) for k, v in data.items()}
    elif isinstance(data, list):
        return [resolve_secrets(v) for v in data]
    elif isinstance(data, str):
        return _resolve_string(data)
    else:
        return data

def _resolve_string(val: str) -> str:
    def replacer(match):
        var_spec = match.group(1)
        # Handle default values like ${VAR:default}
        if ":" in var_spec:
            var_name, default_val = var_spec.split(":", 1)
        else:
            var_name, default_val = var_spec, ""

        # Try Vault first if configured
        vault_val = _fetch_from_vault(var_name)
        if vault_val is not None:
            return vault_val
            
        # Fallback to OS env
        return os.environ.get(var_name, default_val)

    return SECRET_PATTERN.sub(replacer, val)

def _fetch_from_vault(var_name: str) -> str | None:
    vault_addr = os.environ.get("VAULT_ADDR")
    vault_token = os.environ.get("VAULT_TOKEN")
    if not vault_addr or not vault_token:
        return None

    # Expected format for vault secrets in var_name: vault:secret/data/my-secret#key
    if not var_name.startswith("vault:"):
        return None
        
    path_and_key = var_name[6:] # remove "vault:"
    if "#" in path_and_key:
        path, key = path_and_key.split("#", 1)
    else:
        path, key = path_and_key, "value"

    url = f"{vault_addr}/v1/{path}"
    headers = {"X-Vault-Token": vault_token}
    try:
        resp = requests.get(url, headers=headers, timeout=5)
        if resp.status_code == 200:
            data = resp.json()
            return data.get("data", {}).get("data", {}).get(key)
    except Exception:
        pass
    return None
