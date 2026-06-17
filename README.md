# PiGuard-Hybrid

[🇮🇹 Italiano](#italiano) | [🇬🇧 English](#english)

---

<a name="italiano"></a>
## 🇮🇹 Italiano

**PiGuard-Hybrid** è un watchdog avanzato e un demone di automonitoraggio Python leggero e standalone, progettato specificamente per le esigenze di un Raspberry Pi 4 (basato su sistemi operativi Debian/Ubuntu).

Il suo obiettivo primario è **monitorare costantemente la salute del sistema** (RAM, CPU, I/O Dischi, Rete) e **prevenire proattivamente blocchi o crash totali** (spesso causati dall'esaurimento della memoria) applicando azioni correttive autonome su container Docker e servizi systemd nativi. Non è solo un sistema di allerta, ma un sistema di "Self-Healing" (auto-guarigione).

Include inoltre una **Enterprise Web Dashboard** integrata ("Cyber-Grid Dark") per visualizzare le metriche e i log in tempo reale.

---

### ✨ Funzionalità Architetturali e Monitoraggio

PiGuard-Hybrid opera su più livelli per fornire una panoramica completa:

1. **Monitoraggio Ibrido Globale:**
   - **Memoria e CPU:** Legge direttamente da `/proc/meminfo` e `/proc/stat` per ottenere un consumo accurato senza pesare sulle risorse.
   - **Rete (Network I/O):** Analizza `/proc/net/dev` per estrarre la larghezza di banda istantanea (Rx/Tx) e calcola i tassi di pacchetti persi (drop rate) per rilevare problemi di congestione.
   - **Storage e MergerFS Matrix:** Indispensabile per chi usa pool di dischi (come MergerFS). PiGuard non guarda solo il disco principale, ma analizza `/proc/diskstats` per monitorare le performance di **ogni singolo disco fisico** sottostante (velocità di R/W, IOPS, lunghezza della coda, utilizzo percentuale), isolando istantaneamente il disco che causa colli di bottiglia (I/O Wait).

2. **Analisi dei Processi (Systemd & Docker):**
   - PiGuard interroga sia `systemd-cgtop` per i servizi nativi dell'OS, sia `docker stats` per i container.
   - Unisce i dati in un'unica classifica universale, normalizzando i valori per scoprire esattamente "chi" sta affamando il sistema, ordinandoli per consumo I/O o RAM.

---

### 🛡️ Logica di Mitigazione Autonoma (Self-Healing)

PiGuard interviene da solo quando il sistema entra in crisi, seguendo un approccio a due livelli di gravità:

- **Livello 1 - Crisi di Memoria Lieve (RAM Libera < 10%):**
  Il demone avvia automaticamente uno svuotamento sicuro della cache del filesystem (`sync && echo 3 > /proc/sys/vm/drop_caches`). Questo spesso risolve i blocchi legati a intensi trasferimenti di file senza interrompere i servizi.

- **Livello 2 - Crisi di Memoria Critica (RAM Libera < 5%):**
  Se lo svuotamento non basta, PiGuard identifica in autonomia il processo che sta consumando più memoria (che sia un container Docker o un servizio nativo) e **lo riavvia in modo sicuro** (`systemctl restart` o `docker restart`).

- **Sicurezza tramite Whitelist:** Tramite configurazione, è possibile (e consigliato) indicare quali servizi non devono **mai** essere toccati (es. `ssh.service`, `networking.service`, `docker.service`). PiGuard li ignorerà sempre, passando al processo successivo.

---

### 🖥️ Dashboard Web Enterprise Integrata

PiGuard espone una dashboard web integrata e ultra-leggera gestita tramite Flask, accessibile via browser.
- **Porta di default:** `8123`
- **Design "Cyber-Grid Dark":** Interfaccia premium, scura e pulita in stile Datadog/Grafana (Tailwind CSS + Chart.js).
- **Physical Storage Matrix:** Ogni disco fisico appare come un "hardware-blade" indipendente che si illumina di giallo o rosso se va sotto stress I/O.
- **System Flight Log:** Un emulatore di terminale integrato che mostra un "registratore di volo" in tempo reale degli eventi di sistema (avvisi di rete, interventi sui processi, flush di cache).

---

### ⚙️ Installazione e Configurazione

#### 1. Clonazione e Setup
Il progetto include uno script automatizzato che posiziona i file corretti, installa le dipendenze (Flask tramite apt/pip) e configura PiGuard come demone systemd, avviandolo in background.

```bash
git clone <repository_url>
cd <repository_folder>
sudo ./install.sh
```

#### 2. Configurazione (`config.json`)
Al termine dell'installazione, lo script genererà un file in `/etc/piguard/config.json`. **Apri e modifica questo file per adattarlo alle tue necessità**.
Esempio di configurazione:
```json
{
    "ram_cache_drop_threshold_percent": 10.0,
    "ram_remediation_threshold_percent": 5.0,
    "cpu_temp_threshold_celsius": 85.0,
    "whitelist_services": [
        "ssh.service",
        "sshd.service",
        "networking.service",
        "docker.service"
    ],
    "whitelist_containers": [
        "homeassistant",
        "pihole"
    ]
}
```

#### 3. Gestione e Log
- **Accesso Dashboard:** Apri il browser all'indirizzo `http://<IP_DEL_TUO_RASPBERRY>:8123`
- **Gestione del servizio:** Puoi avviare, fermare o riavviare il demone con: `sudo systemctl restart piguard.service`
- **Visualizzare i log base:** `journalctl -u piguard.service -f`
- **Crash Log Persistenti:** In caso di crash critici, il "registratore di volo" riverserà gli ultimi 5 minuti di dati storici nel file `/var/log/piguard_crash.log`.

---
<br><br>

<a name="english"></a>
## 🇬🇧 English

**PiGuard-Hybrid** is an advanced watchdog and lightweight, standalone Python self-monitoring daemon specifically designed for the strict resource constraints of a Raspberry Pi 4 (running Debian/Ubuntu-based OS).

Its primary objective is to **constantly monitor system health** (RAM, CPU, Disk I/O, Network) and **proactively prevent total freezes or crashes** (often caused by out-of-memory states) by applying autonomous corrective actions on Docker containers and native systemd services. It is not just an alerting tool; it is a "Self-Healing" system.

It also features a built-in **Enterprise Web Dashboard** ("Cyber-Grid Dark") to visualize real-time metrics and logs.

---

### ✨ Architectural Features and Monitoring

PiGuard-Hybrid operates on multiple layers to provide a comprehensive overview:

1. **Global Hybrid Monitoring:**
   - **Memory & CPU:** Reads directly from `/proc/meminfo` and `/proc/stat` for highly accurate, zero-overhead tracking.
   - **Network I/O:** Parses `/proc/net/dev` to extract instantaneous bandwidth (Rx/Tx) and calculates packet drop rates to detect network congestion.
   - **Storage & MergerFS Matrix:** Crucial for disk pools (like MergerFS setups). PiGuard doesn't just look at the global mount; it parses `/proc/diskstats` to track the performance of **each underlying physical drive** independently (R/W speeds, IOPS, queue lengths, utilization percentage), instantly isolating whichever drive is causing an I/O Wait bottleneck.

2. **Process Analytics (Systemd & Docker):**
   - PiGuard interfaces with `systemd-cgtop` for native OS services and `docker stats` for containers.
   - It unifies these streams into a single universal leaderboard, normalizing the values to pinpoint exactly "who" is starving the system, sortable by Disk I/O or RAM footprint.

---

### 🛡️ Autonomous Mitigation Logic (Self-Healing)

PiGuard intervenes on its own when the system enters a crisis, using a two-tier severity approach:

- **Level 1 - Mild Memory Crisis (Free RAM < 10%):**
  The daemon automatically triggers a safe filesystem cache flush (`sync && echo 3 > /proc/sys/vm/drop_caches`). This safely resolves heavy file-transfer memory locking without killing services.

- **Level 2 - Critical Memory Crisis (Free RAM < 5%):**
  If flushing isn't enough, PiGuard autonomously identifies the absolute highest memory-consuming process (whether it's a Docker container or a native service) and **safely restarts it** (`systemctl restart` or `docker restart`).

- **Whitelist Protection:** Via configuration, you can (and should) specify which critical services must **never** be touched (e.g., `ssh.service`, `networking.service`, `docker.service`). PiGuard will always skip these and target the next highest consumer.

---

### 🖥️ Built-in Enterprise Web Dashboard

PiGuard serves an ultra-lightweight, built-in web dashboard driven by Flask.
- **Default Port:** `8123`
- **"Cyber-Grid Dark" Design:** A premium, clean, dark-themed UI inspired by Datadog/Grafana (Tailwind CSS + Chart.js).
- **Physical Storage Matrix:** Every physical disk is rendered as an independent "hardware-blade" that glows amber or crimson if it suffers an I/O stress spike.
- **System Flight Log:** An integrated terminal emulator displaying a real-time "flight recorder" of system events (network drop warnings, process restarts, cache flushes).

---

### ⚙️ Installation and Configuration

#### 1. Cloning and Setup
The project includes an automated script that moves the correct files, installs required dependencies (Flask via apt/pip), configures PiGuard as a background systemd daemon, and enables it on boot.

```bash
git clone <repository_url>
cd <repository_folder>
sudo ./install.sh
```

#### 2. Configuration (`config.json`)
After installation, the setup script generates a file at `/etc/piguard/config.json`. **You must open and edit this file to suit your environment**.
Configuration Example:
```json
{
    "ram_cache_drop_threshold_percent": 10.0,
    "ram_remediation_threshold_percent": 5.0,
    "cpu_temp_threshold_celsius": 85.0,
    "whitelist_services": [
        "ssh.service",
        "sshd.service",
        "networking.service",
        "docker.service"
    ],
    "whitelist_containers": [
        "homeassistant",
        "pihole"
    ]
}
```

#### 3. Management and Logs
- **Dashboard Access:** Open your browser to `http://<YOUR_RASPBERRY_IP>:8123`
- **Service Management:** You can start, stop, or restart the background daemon via: `sudo systemctl restart piguard.service`
- **View Base Logs:** `journalctl -u piguard.service -f`
- **Persistent Crash Logs:** In the event of critical thresholds being hit, the "flight recorder" will dump the last 5 minutes of high-frequency historical data to `/var/log/piguard_crash.log`.
