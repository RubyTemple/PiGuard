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

def get_top_systemd_processes():
    """
    Finds top memory consuming systemd services using `systemd-cgtop` or similar.
    We can use `systemctl status` but `systemd-cgtop --batch -n 1` is better for resources.
    Returns list of dicts: [{'name': 'service_name', 'mem_bytes': int, 'cpu_percent': float, 'disk_io': str}]
    """
    try:
        # systemd-cgtop -b -n 1 -m
        # Output:
        # Control Group                                       Tasks   %CPU   Memory  Input/s Output/s
        # /                                                     105      -     1.2G        -        -
        # /system.slice                                          55      -     500M        -        -
        # /system.slice/docker.service                           15      -     200M        -        -
        res = subprocess.run(['systemd-cgtop', '--batch', '-n', '1', '-m'], capture_output=True, text=True, timeout=10)
        services = []
        lines = res.stdout.strip().split('\n')[1:] # Skip header
        for line in lines:
            parts = line.split()
            if not parts:
                continue
            cgroup = parts[0]
            if cgroup.startswith('/system.slice/') and cgroup.endswith('.service'):
                service_name = cgroup.split('/')[-1]
                # Try to parse memory
                if len(parts) >= 4:
                    mem_str = parts[3]
                    mem_bytes = 0
                    if mem_str.endswith('B'):
                        mem_str = mem_str[:-1]
                    try:
                        multiplier = 1
                        if mem_str.endswith('K'):
                            multiplier = 1024
                            mem_str = mem_str[:-1]
                        elif mem_str.endswith('M'):
                            multiplier = 1024 * 1024
                            mem_str = mem_str[:-1]
                        elif mem_str.endswith('G'):
                            multiplier = 1024 * 1024 * 1024
                            mem_str = mem_str[:-1]
                        elif mem_str == '-':
                            mem_str = '0'
                        mem_bytes = float(mem_str) * multiplier

                        cpu_perc = 0.0
                        if len(parts) >= 3 and parts[2] != '-':
                            try: cpu_perc = float(parts[2])
                            except: pass

                        # IO read/write from cgtop is usually column 4 and 5 (Input/s Output/s)
                        disk_io = "0B / 0B"
                        if len(parts) >= 6:
                            io_in = parts[4] if parts[4] != '-' else '0B'
                            io_out = parts[5] if parts[5] != '-' else '0B'
                            disk_io = f"{io_in} / {io_out}"

                        services.append({
                            'name': service_name,
                            'mem_bytes': mem_bytes,
                            'cpu_percent': cpu_perc,
                            'disk_io': disk_io,
                            'type': 'systemd'
                        })
                    except ValueError:
                        pass
        services.sort(key=lambda x: x['mem_bytes'], reverse=True)
        return services
    except Exception:
        return []

def get_top_resource_hog():
    """
    Combines Docker and systemd metrics to find the absolute highest memory consumer.
    Since Docker reports %, and systemd reports bytes, we normalize using total RAM.
    """
    _, _, total_ram_kb, _, _ = get_ram_usage()
    if total_ram_kb == 0:
        return None

    total_ram_bytes = total_ram_kb * 1024

    dockers = get_top_docker_processes()
    systemds = get_top_systemd_processes()

    # Convert docker % to bytes for comparison
    for d in dockers:
        d['mem_bytes'] = (d['mem_percent'] / 100.0) * total_ram_bytes

    all_procs = dockers + systemds
    all_procs.sort(key=lambda x: x['mem_bytes'], reverse=True)

    if all_procs:
        return all_procs[0]
    return None
