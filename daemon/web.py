from flask import Flask, jsonify, render_template
import threading
import os

from monitor import get_ram_usage, get_cpu_temp, get_cpu_load, get_io_wait, get_top_docker_processes, get_top_os_processes, get_network_io, get_disk_metrics

app = Flask(__name__)

# We need a reference to the flight recorder to get logs
flight_recorder_ref = None

def set_flight_recorder(recorder):
    global flight_recorder_ref
    flight_recorder_ref = recorder

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/metrics')
def api_metrics():
    free_ram_percent, free_kb, total_kb, swap_used_kb, swap_total_kb = get_ram_usage()
    used_ram_percent = 100.0 - free_ram_percent if total_kb > 0 else 0
    cpu_temp = get_cpu_temp()
    cpu_load = get_cpu_load()
    io_wait = get_io_wait()

    net_io = get_network_io()
    disk_metrics = get_disk_metrics()

    # Calculate a mock health score based on metrics
    health = 100.0
    if used_ram_percent > 80: health -= (used_ram_percent - 80)
    if cpu_load > 80: health -= (cpu_load - 80)
    if io_wait > 10: health -= (io_wait * 2)
    health = max(0, min(100, health))

    return jsonify({
        'cpu': {
            'load': round(cpu_load, 1),
            'temp': round(cpu_temp, 1)
        },
        'memory': {
            'used_percent': round(used_ram_percent, 1),
            'free_kb': free_kb,
            'total_kb': total_kb,
            'swap_used_kb': swap_used_kb,
            'swap_total_kb': swap_total_kb
        },
        'io_wait': round(io_wait, 1),
        'health_score': round(health, 0),
        'network': net_io,
        'disks': disk_metrics
    })

@app.route('/api/processes')
def api_processes():
    dockers = get_top_docker_processes()
    os_procs = get_top_os_processes()

    # In some situations, a single app runs as multiple processes (like chrome-headless)
    # We should merge processes with the exact same name for a cleaner view.

    merged_os_procs = {}
    for p in os_procs:
        name = p['name']
        if name in merged_os_procs:
            merged_os_procs[name]['cpu_percent'] += p['cpu_percent']
            merged_os_procs[name]['mem_percent'] += p['mem_percent']
            merged_os_procs[name]['mem_bytes'] += p['mem_bytes']
        else:
            merged_os_procs[name] = p.copy()

    # Create a list from the merged OS processes dict
    collapsed_os_procs = list(merged_os_procs.values())

    # Extract lowercased docker names to filter out duplicates in OS processes
    # A bit more specific: we only filter if it exactly matches,
    # to avoid falsely hiding unrelated apps if substring match is too broad.
    docker_names = {d['name'].lower() for d in dockers}

    # Also skip known common docker daemon processes from the OS list since they are "infra"
    # and we already monitor the containers themselves
    infra_names = {'containerd', 'dockerd', 'docker-proxy'}

    filtered_os_procs = []
    for o in collapsed_os_procs:
        o_name = o['name'].lower()

        # Don't show docker infra processes
        if o_name in infra_names:
            continue

        is_duplicate = False
        for d_name in docker_names:
             # Just do a strict match, or if the container name is a prefix of the OS process
             # to avoid hiding e.g. a native DB if there's also a container named "db" that's unrelated
             # But usually people name containers same as the app. Let's do exact match or if it's the exact same string
             if o_name == d_name or d_name.startswith(o_name):
                 is_duplicate = True
                 break
        if not is_duplicate:
            filtered_os_procs.append(o)

    # For a unified list, combine and sort by mem_percent
    all_procs = dockers + filtered_os_procs
    all_procs.sort(key=lambda x: x.get('mem_percent', 0), reverse=True)

    return jsonify({'processes': all_procs[:15]})

@app.route('/api/logs')
def api_logs():
    logs = []
    if flight_recorder_ref:
        # Convert deque to list
        logs = [line for timestamp, line in flight_recorder_ref.history]
    return jsonify({'logs': logs})

def start_web_server(port=8123):
    # Disable flask logging to keep stdout clean
    import logging
    log = logging.getLogger('werkzeug')
    log.setLevel(logging.ERROR)
    app.run(host='0.0.0.0', port=port, debug=False, use_reloader=False)

def run_web_server_thread(recorder, port=8123):
    set_flight_recorder(recorder)
    thread = threading.Thread(target=start_web_server, args=(port,), daemon=True)
    thread.start()
    return thread
