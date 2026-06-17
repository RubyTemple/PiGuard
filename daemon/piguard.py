import time
import sys

from config import load_config
from logger import FlightRecorder
from monitor import get_ram_usage, get_cpu_temp, get_top_resource_hog
from remediation import drop_caches, restart_target
from monitor import get_network_io, get_disk_metrics
from web import run_web_server_thread

def main():
    config = load_config()
    logger = FlightRecorder()

    logger.log("PiGuard started.")

    try:
        run_web_server_thread(logger, port=8123)
        logger.log("Web dashboard started on port 8123.")
    except Exception as e:
        logger.log(f"Failed to start web dashboard: {e}")

    drop_threshold = config.get('ram_cache_drop_threshold_percent', 10.0)
    remediation_threshold = config.get('ram_remediation_threshold_percent', 5.0)

    # Simple cooldown mechanism to avoid endless restarting
    last_remediation_time = 0
    remediation_cooldown = 60 # 1 minute

    last_cache_drop_time = 0
    cache_drop_cooldown = 30 # 30 seconds

    while True:
        try:
            free_ram_percent, free_kb, total_kb, swap_used, swap_total = get_ram_usage()
            cpu_temp = get_cpu_temp()

            logger.log(f"Metrics - RAM Free: {free_ram_percent:.2f}% ({free_kb}KB / {total_kb}KB), CPU Temp: {cpu_temp:.1f}C")

            # Check for network anomalies
            net = get_network_io()
            # Log only if there's an active rate of drops (>0 drops per second)
            if net.get('rx_drops_rate', 0) > 0 or net.get('tx_drops_rate', 0) > 0:
                logger.log(f"[NETWORK WARNING] Interface dropping packets (Rx/s: {net.get('rx_drops_rate', 0):.1f}, Tx/s: {net.get('tx_drops_rate', 0):.1f})")

            # Check for storage anomalies
            disks = get_disk_metrics()
            for dev, stats in disks.items():
                if stats['utilization'] >= 95.0:
                    logger.log(f"[STORAGE WARNING] Drive /dev/{dev} reached {stats['utilization']:.1f}% I/O utilization - Latency spike predicted")

            now = time.time()

            # Level 1: RAM < 10% -> Drop caches
            if free_ram_percent < drop_threshold:
                if now - last_cache_drop_time > cache_drop_cooldown:
                    logger.log(f"🚨 GUARD ACTION: RAM Free ({free_ram_percent:.2f}%) below {drop_threshold}%. Initiating safe cache flush.")
                    logger.dump_crash_log("RAM_WARNING_CACHE_DROP")
                    drop_caches(logger)
                    last_cache_drop_time = time.time()

            # Level 2: RAM < 5% -> Find hog and restart
            if free_ram_percent < remediation_threshold:
                if now - last_remediation_time > remediation_cooldown:
                    logger.log(f"🚨 GUARD ACTION: RAM Critical ({free_ram_percent:.2f}%). Seeking top resource hog to cut.")
                    logger.dump_crash_log("RAM_CRITICAL_RESTART")

                    hog = get_top_resource_hog()
                    if hog:
                        mb_used = hog.get('mem_bytes', 0) / (1024*1024)
                        cpu_used = hog.get('cpu_percent', 0.0)
                        logger.log(f"✂️ CUT ACTION: Target identified -> {hog['name']} [{hog['type']}] (RAM: {mb_used:.1f}MB, CPU: {cpu_used}%)")
                        success = restart_target(hog, config, logger)
                        if success:
                            last_remediation_time = time.time()
                        else:
                            # If we failed (e.g., due to whitelist), we shouldn't just spam. We could implement
                            # a backoff or try the next hog, but for now we'll just log and continue.
                            # We update the last_remediation_time anyway to avoid tight loop on a whitelisted hog.
                            last_remediation_time = time.time()
                            logger.log(f"✂️ CUT SKIPPED: Remediation failed or bypassed for {hog['name']}.")
                    else:
                        logger.log("✂️ CUT FAILED: Could not identify top resource hog.")

        except Exception as e:
            logger.log(f"Unexpected error in main loop: {e}")

        # Sleep to be lightweight
        time.sleep(5)

if __name__ == '__main__':
    main()
