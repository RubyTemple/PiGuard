import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), 'daemon')))

import time
from config import load_config
from logger import FlightRecorder
from monitor import get_ram_usage, get_cpu_temp

print("Starting PiGuard Mock Test...")

config = load_config('config/config.json')
print(f"Loaded config keys: {list(config.keys())}")

logger = FlightRecorder(max_history_seconds=10)
logger.log("Test log entry")

free_ram_percent, free_kb, total_kb, swap_used, swap_total = get_ram_usage()
cpu_temp = get_cpu_temp()

print(f"Current System RAM Free: {free_ram_percent:.2f}% ({free_kb}/{total_kb} KB)")
print(f"Current CPU Temp: {cpu_temp}C")

logger.dump_crash_log("MOCK_CRASH_TEST")
print("Crash log dumped. Check /var/log/piguard_crash.log (if permitted) or just no crash.")

print("Mock test completed successfully.")
