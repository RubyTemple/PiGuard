import subprocess

def drop_caches(logger):
    """
    Safely flushes filesystem caches.
    """
    logger.log("Esecuzione svuotamento cache sicura (sync && drop_caches)")
    try:
        subprocess.run(['sync'], check=True, timeout=10)
        # Using subprocess to write to /proc/sys/vm/drop_caches might require shell=True
        # Or we can write directly in python if run as root.
        with open('/proc/sys/vm/drop_caches', 'w') as f:
            f.write("3\n")
        logger.log("Svuotamento cache completato con successo.")
        return True
    except Exception as e:
        logger.log(f"Errore durante lo svuotamento cache: {e}")
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

    if target_type == 'systemd' or target_type == 'os':
        if name in config.get('whitelist_services', []):
            logger.log(f"Ignorato servizio OS {name} (protetto in whitelist).")
            return False
        logger.log(f"Riavvio del servizio: {name}")
        try:
            subprocess.run(['systemctl', 'restart', name], check=True, timeout=30)
            logger.log(f"Riavviato con successo: {name}")
            return True
        except subprocess.CalledProcessError as e:
            logger.log(f"Fallito riavvio di {name}: {e}")
            return False

    elif target_type == 'docker':
        if name in config.get('whitelist_containers', []):
            logger.log(f"Ignorato container {name} (protetto in whitelist).")
            return False
        logger.log(f"Riavvio del container docker: {name}")
        try:
            subprocess.run(['docker', 'restart', name], check=True, timeout=30)
            logger.log(f"Riavviato con successo il container {name}")
            return True
        except subprocess.CalledProcessError as e:
            logger.log(f"Fallito riavvio del container {name}: {e}")
            return False

    return False
