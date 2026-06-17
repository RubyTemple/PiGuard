import collections
import time
import datetime
import os

FLIGHT_RECORDER_PATH = '/tmp/piguard_flight_recorder.log'
CRASH_LOG_PATH = '/var/log/piguard_crash.log'

class FlightRecorder:
    def __init__(self, max_history_seconds=300):
        # We will keep lines in a deque.
        # Since we might log multiple times per second, we'll store (timestamp, line)
        self.history = collections.deque()
        self.max_history_seconds = max_history_seconds

    def log(self, message):
        now = time.time()
        timestamp_str = datetime.datetime.fromtimestamp(now).strftime('%Y-%m-%d %H:%M:%S')
        log_line = f"[{timestamp_str}] {message}"
        self.history.append((now, log_line))

        # Prune old logs
        while self.history and self.history[0][0] < now - self.max_history_seconds:
            self.history.popleft()

        # Also write to tmpfs. Instead of appending forever, we'll rewrite the file
        # every 10 logs to prevent memory leaks in tmpfs.
        try:
            if not hasattr(self, '_log_count'):
                self._log_count = 0
            self._log_count += 1
            if self._log_count % 10 == 0:
                with open(FLIGHT_RECORDER_PATH, 'w') as f:
                    for _, l in self.history:
                        f.write(l + '\n')
            else:
                with open(FLIGHT_RECORDER_PATH, 'a') as f:
                    f.write(log_line + '\n')
        except Exception:
            pass

    def dump_crash_log(self, reason):
        try:
            with open(CRASH_LOG_PATH, 'a') as f:
                now_str = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                f.write(f"\n====================================\n")
                f.write(f"PIGUARD CRASH DUMP AT {now_str}\n")
                f.write(f"REASON: {reason}\n")
                f.write(f"--- 5 MINUTE FLIGHT RECORDER LOG ---\n")
                for _, line in self.history:
                    f.write(line + '\n')
                f.write(f"====================================\n\n")
        except Exception as e:
            print(f"Failed to dump crash log: {e}")
