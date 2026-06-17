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

    # To fix concurrency bug between web polling and daemon loop:
    # Only update deltas if enough time has passed (e.g. > 1 sec) or if it's the daemon doing it.
    # A cleaner approach for this specific bug is to not update `last_*` states if the time diff is too small,
    # or just use a small window.
    if last_net_time > 0 and current_time > last_net_time:
        time_diff = current_time - last_net_time
        if time_diff >= 1.0:
            rx_bps = (current_rx - last_net_rx) / time_diff
            tx_bps = (current_tx - last_net_tx) / time_diff
            rx_drops_rate = (drops_rx - last_net_drops_rx) / time_diff
            tx_drops_rate = (drops_tx - last_net_drops_tx) / time_diff
            rx_errors_rate = (errors_rx - last_net_errs_rx) / time_diff
            tx_errors_rate = (errors_tx - last_net_errs_tx) / time_diff

            # Update state ONLY when we calculate new rates
            last_net_rx = current_rx
            last_net_tx = current_tx
            last_net_drops_rx = drops_rx
            last_net_drops_tx = drops_tx
            last_net_errs_rx = errors_rx
            last_net_errs_tx = errors_tx
            last_net_time = current_time

            # Store these globally so if time_diff < 1.0 we return cached
            global cached_net_stats
            cached_net_stats = {
                'rx_bps': max(0.0, rx_bps),
                'tx_bps': max(0.0, tx_bps),
                'rx_drops_rate': max(0.0, rx_drops_rate),
                'tx_drops_rate': max(0.0, tx_drops_rate),
                'rx_errors_rate': max(0.0, rx_errors_rate),
                'tx_errors_rate': max(0.0, tx_errors_rate)
            }
            return cached_net_stats
        else:
            # Return cached if polled too soon (concurrent access)
            if 'cached_net_stats' in globals():
                return cached_net_stats
    else:
        # Initial run
        last_net_rx = current_rx
        last_net_tx = current_tx
        last_net_drops_rx = drops_rx
        last_net_drops_tx = drops_tx
        last_net_errs_rx = errors_rx
        last_net_errs_tx = errors_tx
        last_net_time = current_time

    return {
        'rx_bps': 0.0, 'tx_bps': 0.0, 'rx_drops_rate': 0.0, 'tx_drops_rate': 0.0, 'rx_errors_rate': 0.0, 'tx_errors_rate': 0.0
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

        if time_diff >= 1.0:
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

            last_diskstats = current_stats
            last_disk_time = current_time

            global cached_disk_stats
            cached_disk_stats = metrics
            return metrics
        else:
            if 'cached_disk_stats' in globals():
                # We also need to update queue length from current even if returning cached
                for dev in cached_disk_stats:
                    if dev in current_stats:
                        cached_disk_stats[dev]['queue_length'] = current_stats[dev]['queue']
                return cached_disk_stats
            else:
                return {}
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

                # We need absolute memory size as well
                mem_usage_str = data.get('MemUsage', '0B / 0B')
                # e.g. "400MiB / 8GiB"
                mem_bytes = 0
                mem_val_str = mem_usage_str.split(' / ')[0].strip()
                try:
                    # simplistic parse
                    val = float(''.join(c for c in mem_val_str if c.isdigit() or c == '.'))
                    if 'GiB' in mem_val_str or 'GB' in mem_val_str: val *= 1024 * 1024 * 1024
                    elif 'MiB' in mem_val_str or 'MB' in mem_val_str: val *= 1024 * 1024
                    elif 'KiB' in mem_val_str or 'KB' in mem_val_str: val *= 1024
                    mem_bytes = val
                except: pass

                block_io = data.get('BlockIO', '0B / 0B')
                net_io = data.get('NetIO', '0B / 0B')

                # Mock a disk_io_percent based on block_io values
                # Just for visual consistency as requested, assuming max 1GB throughput
                disk_io_percent = 0.0
                try:
                    val = float(''.join(c for c in block_io.split('/')[0].strip() if c.isdigit() or c == '.'))
                    if 'GB' in block_io: disk_io_percent = min(100.0, (val * 1024) / 10.24)
                    elif 'MB' in block_io: disk_io_percent = min(100.0, val / 10.24)
                    elif 'KB' in block_io: disk_io_percent = min(100.0, (val / 1024) / 10.24)
                except:
                    pass

                containers.append({
                    'name': name,
                    'mem_percent': mem_perc,
                    'mem_bytes': mem_bytes,
                    'cpu_percent': cpu_perc,
                    'disk_io': block_io,
                    'disk_io_percent': disk_io_percent,
                    'net_io': net_io,
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

last_os_io_stats = {}
last_os_io_time = 0

def get_top_os_processes():
    """
    Finds top memory/cpu consuming processes using generic `ps` to capture EVERYTHING natively.
    Returns list of dicts: [{'name': 'process_name', 'mem_bytes': int, 'cpu_percent': float, 'disk_io': str, 'type': 'os'}]
    """
    global last_os_io_stats, last_os_io_time
    current_time = time.time()

    try:
        # Get PIDs as well to read /proc/[pid]/io
        # Increase the limit slightly because we will filter out Docker processes
        res = subprocess.run(['ps', '-e', '-o', 'pid,comm,%cpu,%mem,rss', '--sort=-%mem'], capture_output=True, text=True, timeout=10)
        processes = []
        lines = res.stdout.strip().split('\n')[1:40] # Skip header, get top 40 to ensure we have enough after filtering

        current_io_stats = {}

        for line in lines:
            parts = line.split()
            if len(parts) >= 5:
                pid = parts[0]

                # Exclude processes that belong to Docker containers to prevent duplicates
                is_docker = False
                try:
                    with open(f'/proc/{pid}/cgroup', 'r') as f:
                        cgroup_data = f.read()
                        if 'docker' in cgroup_data or 'kubepods' in cgroup_data or 'containerd' in cgroup_data:
                            is_docker = True
                except Exception:
                    pass

                if is_docker:
                    continue

                # Name might have spaces, so we merge all but the last 3 cols
                name = " ".join(parts[1:-3])
                try:
                    cpu_perc = float(parts[-3])
                    mem_perc = float(parts[-2])
                    rss_kb = float(parts[-1])
                    mem_bytes = rss_kb * 1024

                    # Attempt to read /proc/[pid]/io for disk stats
                    io_str = "-"
                    try:
                        with open(f'/proc/{pid}/io', 'r') as f:
                            read_bytes = 0
                            write_bytes = 0
                            for io_line in f:
                                if io_line.startswith('read_bytes:'):
                                    read_bytes = int(io_line.split()[1])
                                elif io_line.startswith('write_bytes:'):
                                    write_bytes = int(io_line.split()[1])

                            current_io_stats[pid] = {'r': read_bytes, 'w': write_bytes}

                            # Docker 'BlockIO' typically returns cumulative IO, not rate.
                            # Let's align OS IO with that for a consistent view instead of instantaneous rate,
                            # or just use cumulative bytes here directly to match Docker stats BlockIO format.
                            # Format nicely
                            def fmt(b):
                                if b > 1024*1024*1024: return f"{b/1024/1024/1024:.1f}GB"
                                if b > 1024*1024: return f"{b/1024/1024:.1f}MB"
                                if b > 1024: return f"{b/1024:.1f}KB"
                                return f"{b:.0f}B"

                            io_str = f"{fmt(read_bytes)} / {fmt(write_bytes)}"
                    except Exception:
                        pass # IO reading requires root or might fail if process dies

                    processes.append({
                        'name': name,
                        'mem_bytes': mem_bytes,
                        'mem_percent': mem_perc,
                        'cpu_percent': cpu_perc,
                        'disk_io': io_str,
                        'net_io': '-', # OS processes don't easily expose per-process net IO without root tools like nethogs
                        'type': 'os'
                    })
                except ValueError:
                    pass

        # Update state only if we advanced time reasonably
        if current_time - last_os_io_time >= 1.0:
            last_os_io_stats = current_io_stats
            last_os_io_time = current_time

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
