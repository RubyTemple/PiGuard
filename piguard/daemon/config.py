import json
import os

DEFAULT_CONFIG_PATH = '/etc/piguard/config.json'

DEFAULT_CONFIG = {
    "ram_cache_drop_threshold_percent": 10.0,
    "ram_remediation_threshold_percent": 5.0,
    "cpu_temp_threshold_celsius": 85.0,
    "whitelist_services": [
        "ssh.service",
        "sshd.service",
        "networking.service",
        "systemd-networkd.service",
        "docker.service",
        "piguard.service"
    ],
    "whitelist_containers": [],
    "priority_services_to_kill": [],
    "priority_containers_to_kill": []
}

def load_config(path=DEFAULT_CONFIG_PATH):
    config = DEFAULT_CONFIG.copy()
    if os.path.exists(path):
        try:
            with open(path, 'r') as f:
                user_config = json.load(f)
                config.update(user_config)
        except Exception as e:
            print(f"Error loading config from {path}: {e}")
    return config
