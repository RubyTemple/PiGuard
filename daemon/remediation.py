import subprocess

def drop_caches(logger):
    """
    Safely flushes filesystem caches.
    """
    logger.log("Executing safe cache flush (sync && drop_caches)")
    try:
        subprocess.run(['sync'], check=True, timeout=10)
        # Using subprocess to write to /proc/sys/vm/drop_caches might require shell=True
        # Or we can write directly in python if run as root.
        with open('/proc/sys/vm/drop_caches', 'w') as f:
            f.write("3\n")
        logger.log("Cache flush successful.")
        return True
    except Exception as e:
        logger.log(f"Failed to drop caches: {e}")
        return False

def restart_target(target, config, logger):
    """
    Restarts a systemd service or docker container, checking whitelists first.
    target is a dict: {'name': '...', 'type': 'systemd' or 'docker'}
    """
    name = target.get('name')
    target_type = target.get('type')

    if not name or not target_type:
        return False

    if target_type == 'systemd':
        if name in config.get('whitelist_services', []):
            logger.log(f"Ignoring systemd service {name} as it is whitelisted.")
            return False
        logger.log(f"Restarting systemd service: {name}")
        try:
            subprocess.run(['systemctl', 'restart', name], check=True, timeout=30)
            logger.log(f"Successfully restarted {name}")
            return True
        except subprocess.CalledProcessError as e:
            logger.log(f"Failed to restart {name}: {e}")
            return False

    elif target_type == 'docker':
        if name in config.get('whitelist_containers', []):
            logger.log(f"Ignoring docker container {name} as it is whitelisted.")
            return False
        logger.log(f"Restarting docker container: {name}")
        try:
            subprocess.run(['docker', 'restart', name], check=True, timeout=30)
            logger.log(f"Successfully restarted docker container {name}")
            return True
        except subprocess.CalledProcessError as e:
            logger.log(f"Failed to restart container {name}: {e}")
            return False

    return False
