import os
import subprocess
import json

def get_ram_usage():
    """
    Reads /proc/meminfo to get free and total RAM, as well as Swap.
    Returns (free_percent, free_kb, total_kb, swap_used_kb, swap_total_kb)
    """
    total = 0
    available = 0
    swap_total = 0
    swap_free = 0
    try:
        with open('/proc/meminfo', 'r') as f:
            for line in f:
                if line.startswith('MemTotal:'):
                    total = int(line.split()[1])
                elif line.startswith('MemAvailable:'):
                    available = int(line.split()[1])
                elif line.startswith('SwapTotal:'):
                    swap_total = int(line.split()[1])
                elif line.startswith('SwapFree:'):
                    swap_free = int(line.split()[1])

        # Fallback if MemAvailable is not found, use MemFree + Buffers + Cached (not strictly accurate but decent fallback)
        if available == 0 and total > 0:
             # We should rescan for MemFree, Buffers, Cached but MemAvailable has been in Linux since 3.14 (2014)
             pass

        if total > 0:
            free_percent = (available / total) * 100.0
            swap_used = swap_total - swap_free
            return free_percent, available, total, swap_used, swap_total
    except Exception:
        pass
    return 100.0, 0, 0, 0, 0

last_cpu_idle = 0
last_cpu_total = 0

def get_cpu_load():
    """
    Calculates CPU load percentage over time by reading /proc/stat.
    Returns CPU load percentage (float).
    """
    global last_cpu_idle, last_cpu_total
    try:
        with open('/proc/stat', 'r') as f:
            line = f.readline()
            if line.startswith('cpu '):
                parts = [int(x) for x in line.split()[1:]]
                idle = parts[3] + parts[4] # idle + iowait
                non_idle = parts[0] + parts[1] + parts[2] + parts[5] + parts[6] + parts[7]
                total = idle + non_idle

                total_diff = total - last_cpu_total
                idle_diff = idle - last_cpu_idle

                last_cpu_total = total
                last_cpu_idle = idle

                if total_diff == 0:
                    return 0.0
                return ((total_diff - idle_diff) / total_diff) * 100.0
    except Exception:
        pass
    return 0.0

import time

last_net_rx = 0
last_net_tx = 0
last_net_time = 0
last_net_drops_rx = 0
last_net_drops_tx = 0
last_net_errs_rx = 0
last_net_errs_tx = 0

def get_network_io():
    """
    Reads /proc/net/dev to get total Rx/Tx throughput (bytes/sec) and total drop/error rates.
    Returns dict: {'rx_bps': float, 'tx_bps': float, 'rx_drops': int, 'tx_drops': int, 'rx_errors': int, 'tx_errors': int}
    """
    global last_net_rx, last_net_tx, last_net_time

    current_time = time.time()
    current_rx = 0
    current_tx = 0
    drops_rx = 0
    drops_tx = 0
    errors_rx = 0
    errors_tx = 0

    try:
        with open('/proc/net/dev', 'r') as f:
            lines = f.readlines()[2:] # Skip headers
            for line in lines:
                parts = line.split()
                if not parts:
                    continue
                # format: Interface: rx_bytes rx_packets rx_errs rx_drop rx_fifo rx_frame rx_comp rx_mcast tx_bytes tx_packets tx_errs tx_drop ...
                if parts[0] == 'lo:':
                    continue

                # Handling cases where interface name and bytes are not separated by space
                if ':' in parts[0]:
                    rx_bytes = int(parts[1])
                    rx_errs = int(parts[3])
                    rx_drop = int(parts[4])
                    tx_bytes = int(parts[9])
                    tx_errs = int(parts[11])
                    tx_drop = int(parts[12])
                else:
                    # Depending on format
                    pass

                current_rx += rx_bytes
                current_tx += tx_bytes
                drops_rx += rx_drop
                drops_tx += tx_drop
                errors_rx += rx_errs
                errors_tx += tx_errs
    except Exception:
        pass

    global last_net_drops_rx, last_net_drops_tx, last_net_errs_rx, last_net_errs_tx

    rx_bps = 0.0
    tx_bps = 0.0
    rx_drops_rate = 0.0
    tx_drops_rate = 0.0
    rx_errors_rate = 0.0
    tx_errors_rate = 0.0

    if last_net_time > 0 and current_time > last_net_time:
        time_diff = current_time - last_net_time
        rx_bps = (current_rx - last_net_rx) / time_diff
        tx_bps = (current_tx - last_net_tx) / time_diff
        rx_drops_rate = (drops_rx - last_net_drops_rx) / time_diff
        tx_drops_rate = (drops_tx - last_net_drops_tx) / time_diff
        rx_errors_rate = (errors_rx - last_net_errs_rx) / time_diff
        tx_errors_rate = (errors_tx - last_net_errs_tx) / time_diff

    last_net_rx = current_rx
    last_net_drops_rx = drops_rx
    last_net_drops_tx = drops_tx
    last_net_errs_rx = errors_rx
    last_net_errs_tx = errors_tx
    last_net_tx = current_tx
    last_net_time = current_time

    return {
        'rx_bps': max(0.0, rx_bps),
        'tx_bps': max(0.0, tx_bps),
        'rx_drops_rate': max(0.0, rx_drops_rate),
        'tx_drops_rate': max(0.0, tx_drops_rate),
        'rx_errors_rate': max(0.0, rx_errors_rate),
        'tx_errors_rate': max(0.0, tx_errors_rate)
    }

last_diskstats = {}
last_disk_time = 0

def get_mergerfs_physical_drives():
    """
    Attempts to read /proc/mounts to identify if a mergerfs mount exists,
    and returns a list of base device names underlying it (or just returns all major block devices if not explicitly found).
    Since mergerfs is FUSE, finding the exact underlying drives from mount might be tricky without config parsing.
    Fallback: We return all physical hd*/sd*/nvme* devices found in /proc/diskstats that have activity.
    """
    drives = []
    # Actually, let's just find standard physical disks.
    valid_prefixes = ('sd', 'hd', 'vd', 'nvme')
    try:
        with open('/proc/diskstats', 'r') as f:
            for line in f:
                parts = line.split()
                if len(parts) >= 14:
                    dev_name = parts[2]
                    # ignore partitions (e.g., sda1), keep base block device (e.g., sda)
                    if any(dev_name.startswith(p) for p in valid_prefixes):
                        # Simple partition filter: if it ends in a number, it's usually a partition.
                        # Except nvme0n1.
                        if dev_name.startswith('nvme'):
                            if 'p' in dev_name: continue
                        else:
                            if dev_name[-1].isdigit(): continue
                        drives.append(dev_name)
    except Exception:
        pass
    return drives

def get_disk_metrics():
    """
    Reads /proc/diskstats to calculate IO metrics for physical drives.
    Returns dict of drive_name -> {'read_bps': float, 'write_bps': float, 'iops': float, 'queue_length': float, 'utilization': float}
    """
    global last_diskstats, last_disk_time

    current_time = time.time()
    metrics = {}
    drives_to_monitor = get_mergerfs_physical_drives()

    current_stats = {}
    try:
        with open('/proc/diskstats', 'r') as f:
            for line in f:
                parts = line.split()
                if len(parts) >= 14:
                    dev_name = parts[2]
                    if dev_name not in drives_to_monitor:
                        continue

                    # 3: reads completed
                    # 5: sectors read (usually 512 bytes per sector)
                    # 7: writes completed
                    # 9: sectors written
                    # 11: I/O currently in progress (queue length)
                    # 12: time spent doing I/Os (ms) (utilization)
                    reads = int(parts[3])
                    sectors_read = int(parts[5])
                    writes = int(parts[7])
                    sectors_written = int(parts[9])
                    queue = int(parts[11])
                    io_ticks = int(parts[12])

                    current_stats[dev_name] = {
                        'reads': reads,
                        'sectors_read': sectors_read,
                        'writes': writes,
                        'sectors_written': sectors_written,
                        'queue': queue,
                        'io_ticks': io_ticks
                    }
    except Exception:
        pass

    if last_disk_time > 0 and current_time > last_disk_time:
        time_diff = current_time - last_disk_time

        for dev, stats in current_stats.items():
            if dev in last_diskstats:
                last = last_diskstats[dev]

                d_reads = stats['reads'] - last['reads']
                d_writes = stats['writes'] - last['writes']
                d_sect_read = stats['sectors_read'] - last['sectors_read']
                d_sect_write = stats['sectors_written'] - last['sectors_written']
                d_ticks = stats['io_ticks'] - last['io_ticks']

                iops = (d_reads + d_writes) / time_diff
                read_bps = (d_sect_read * 512) / time_diff
                write_bps = (d_sect_write * 512) / time_diff
                # Utilization = (io_ticks delta in ms) / (time delta in ms) * 100
                utilization = min(100.0, (d_ticks / (time_diff * 1000.0)) * 100.0)

                metrics[dev] = {
                    'read_bps': max(0.0, read_bps),
                    'write_bps': max(0.0, write_bps),
                    'iops': max(0.0, iops),
                    'queue_length': stats['queue'],
                    'utilization': max(0.0, utilization)
                }
            else:
                # First time seeing this disk
                metrics[dev] = {
                    'read_bps': 0.0, 'write_bps': 0.0, 'iops': 0.0,
                    'queue_length': stats['queue'], 'utilization': 0.0
                }
    else:
        for dev, stats in current_stats.items():
             metrics[dev] = {
                    'read_bps': 0.0, 'write_bps': 0.0, 'iops': 0.0,
                    'queue_length': stats['queue'], 'utilization': 0.0
                }

    last_diskstats = current_stats
    last_disk_time = current_time

    return metrics

def get_io_wait():
    """
    Returns Disk I/O Wait percentage.
    Calculated similarly from /proc/stat, specifically the iowait field.
    """
    # For a snapshot metric without maintaining a separate history just for iowait,
    # we can do a quick 0.1s sleep or use a system tool, or we can just read
    # /proc/stat and do a similar delta.
    # To keep it lightweight, we can just return a synthetic or rough approximation from loadavg
    # or implement a specific delta just for iowait. Let's do a simple one.
    try:
        with open('/proc/stat', 'r') as f:
            # We can use vmstat or read iowait directly but it needs a delta.
            # Let's rely on vmstat output if available, else 0.
            # actually we can get it from top or vmstat or directly.
            pass
    except:
        pass

    try:
        res = subprocess.run(['vmstat', '1', '2'], capture_output=True, text=True, timeout=5)
        # Output lines:
        # procs -----------memory---------- ---swap-- -----io---- -system-- ------cpu-----
        #  r  b   swpd   free   buff  cache   si   so    bi    bo   in   cs us sy id wa st
        lines = res.stdout.strip().split('\n')
        if len(lines) >= 4:
            parts = lines[-1].split()
            # wa is usually the 16th column (index 15), but it can vary.
            # Let's search the header.
            headers = lines[1].split()
            if 'wa' in headers:
                idx = headers.index('wa')
                return float(parts[idx])
    except:
        pass
    return 0.0

def get_cpu_temp():
    """
    Reads /sys/class/thermal/thermal_zone0/temp.
    Returns temperature in Celsius.
    """
    try:
        with open('/sys/class/thermal/thermal_zone0/temp', 'r') as f:
            temp_millicelsius = int(f.read().strip())
            return temp_millicelsius / 1000.0
    except Exception:
        pass
    return 0.0

def get_top_docker_processes():
    """
    Executes docker stats and returns a list of containers sorted by MemUsage descending.
    Returns list of dicts: [{'name': 'container_name', 'mem_percent': float, 'cpu_percent': float, 'disk_io': str}]
    """
    try:
        # Check if docker is running
        res = subprocess.run(['systemctl', 'is-active', 'docker'], capture_output=True, text=True, timeout=5)
        if res.stdout.strip() != 'active':
            return []

        # Use docker stats. Format as json.
        res = subprocess.run(['docker', 'stats', '--no-stream', '--format', '{{json .}}'], capture_output=True, text=True, timeout=10)
        containers = []
        for line in res.stdout.strip().split('\n'):
            if not line:
                continue
            try:
                data = json.loads(line)
                name = data.get('Name')
                # MemPerc looks like "0.15%", CPUPerc looks like "0.01%"
                mem_perc_str = data.get('MemPerc', '0%').replace('%', '')
                mem_perc = float(mem_perc_str)

                cpu_perc_str = data.get('CPUPerc', '0%').replace('%', '')
                try: cpu_perc = float(cpu_perc_str)
                except: cpu_perc = 0.0

                block_io = data.get('BlockIO', '0B / 0B')

                containers.append({
                    'name': name,
                    'mem_percent': mem_perc,
                    'cpu_percent': cpu_perc,
                    'disk_io': block_io,
                    'type': 'docker'
                })
            except json.JSONDecodeError:
                pass
            except ValueError:
                pass

        # Sort by mem_percent desc
        containers.sort(key=lambda x: x['mem_percent'], reverse=True)
        return containers
    except Exception:
        return []

def get_top_os_processes():
    """
    Finds top memory/cpu consuming processes using generic `ps` to capture EVERYTHING natively.
    Returns list of dicts: [{'name': 'process_name', 'mem_bytes': int, 'cpu_percent': float, 'disk_io': str, 'type': 'os'}]
    """
    try:
        # ps -e -o comm,%cpu,%mem,rss --sort=-%mem | head -n 20
        res = subprocess.run(['ps', '-e', '-o', 'comm,%cpu,%mem,rss', '--sort=-%mem'], capture_output=True, text=True, timeout=10)
        processes = []
        lines = res.stdout.strip().split('\n')[1:21] # Skip header, get top 20
        for line in lines:
            parts = line.split()
            if len(parts) >= 4:
                # Name might have spaces, so we merge all but the last 3 cols
                name = " ".join(parts[:-3])
                try:
                    cpu_perc = float(parts[-3])
                    mem_perc = float(parts[-2])
                    rss_kb = float(parts[-1])
                    mem_bytes = rss_kb * 1024

                    processes.append({
                        'name': name,
                        'mem_bytes': mem_bytes,
                        'mem_percent': mem_perc,
                        'cpu_percent': cpu_perc,
                        'disk_io': '-', # ps doesn't provide easy per-process IO without iotop (requires root/delays)
                        'type': 'os'
                    })
                except ValueError:
                    pass
        return processes
    except Exception:
        return []

def get_top_resource_hog():
    """
    Combines Docker and OS metrics to find the absolute highest memory consumer.
    """
    _, _, total_ram_kb, _, _ = get_ram_usage()
    if total_ram_kb == 0:
        return None

    total_ram_bytes = total_ram_kb * 1024

    dockers = get_top_docker_processes()
    os_procs = get_top_os_processes()

    # Convert docker % to bytes for comparison
    for d in dockers:
        d['mem_bytes'] = (d['mem_percent'] / 100.0) * total_ram_bytes

    all_procs = dockers + os_procs
    all_procs.sort(key=lambda x: x['mem_bytes'], reverse=True)

    if all_procs:
        return all_procs[0]
    return None
