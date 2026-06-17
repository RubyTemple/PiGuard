# PiGuard-Hybrid

[🇮🇹 Italiano](#italiano) | [🇬🇧 English](#english)

---

<a name="italiano"></a>
## 🇮🇹 Italiano

**PiGuard-Hybrid** è un watchdog e demone di automonitoraggio Python leggero e standalone, progettato specificamente per Raspberry Pi 4 (basato su Debian). Il suo obiettivo è monitorare la salute del sistema e prevenire blocchi o crash causati dall'esaurimento delle risorse da parte di container Docker e servizi systemd nativi, applicando azioni correttive autonome.

Include inoltre una **Enterprise Web Dashboard** integrata con un'estetica moderna (stile "Cyber-Grid Dark") per visualizzare le metriche in tempo reale.

### ✨ Funzionalità Principali

1. **Monitoraggio Ibrido delle Risorse:**
   - Legge direttamente le metriche hardware (RAM, Swap, Temp CPU, I/O Wait) da `/proc` e `/sys`.
   - Analizza l'uso della rete (Rx/Tx, pacchetti persi/errori).
   - Estrae le metriche individuali per i dischi fisici sottostanti (ideale per setup MergerFS), inclusi velocità di lettura/scrittura, IOPS e lunghezza della coda.
   - Si interfaccia con i cgroups di systemd e con le statistiche di Docker per identificare con precisione i processi più pesanti.

2. **Logica di Mitigazione Autonoma (Self-Healing):**
   - **Crisi di Memoria:** Se la RAM libera scende sotto il 10%, avvia automaticamente uno svuotamento sicuro della cache del filesystem (`sync && drop_caches`).
   - **Rimedio Intelligente:** Se la RAM libera scende sotto il 5%, identifica il processo (Docker o systemd) che consuma più risorse e lo riavvia in modo sicuro.
   - Le whitelist configurabili impediscono al sistema di toccare i servizi critici (es. `ssh`, `networking`).

3. **Dashboard Web Enterprise Integrata:**
   - Server web Flask ultra-leggero in esecuzione sulla porta `8123`.
   - Tema scuro e reattivo basato su Tailwind CSS.
   - Visualizza widget per Larghezza di Banda di Rete, CPU, RAM, e I/O Wait.
   - Include una "Physical Storage Matrix" per mostrare le prestazioni dei singoli dischi in tempo reale con avvisi visivi.
   - Registratore di volo in stile terminale per visualizzare gli eventi di sistema e gli interventi autonomi.

### ⚙️ Installazione

Il progetto include uno script automatizzato che posiziona i file, installa le dipendenze (come Flask) e configura il demone come servizio systemd.

```bash
git clone <repository_url> piguard
cd piguard
sudo ./install.sh
```

La configurazione predefinita viene salvata in `/etc/piguard/config.json`. Puoi modificarla per cambiare le soglie di intervento e gestire le whitelist di servizi o container.

Una volta installato, puoi accedere alla dashboard web aprendo il browser all'indirizzo:
`http://<IP_DEL_TUO_RASPBERRY>:8123`

---

<a name="english"></a>
## 🇬🇧 English

**PiGuard-Hybrid** is a lightweight, standalone Python watchdog and self-monitoring daemon explicitly built for Debian-based Raspberry Pi 4 systems. Its purpose is to monitor system health and proactively prevent freezes or crashes caused by resource exhaustion from Docker containers and native systemd services by taking autonomous corrective actions.

It also features a built-in **Enterprise Web Dashboard** with a modern, "Cyber-Grid Dark" aesthetic to visualize real-time telemetry.

### ✨ Core Architecture & Features

1. **Hybrid Resource & Process Monitor:**
   - Reads global hardware metrics (RAM, Swap, CPU Temp, I/O Wait) directly from `/proc` and `/sys`.
   - Analyzes Network I/O (Rx/Tx throughput, packet drops/errors).
   - Extracts individual physical drive metrics (perfect for MergerFS pools) including Read/Write speed, IOPS, and queue lengths.
   - Interfaces with systemd cgroups and Docker stats to precisely identify heavy processes.

2. **Autonomous Mitigation Logic (Self-Healing):**
   - **Memory Crisis:** If free RAM drops below 10%, it immediately triggers a safe filesystem cache flush (`sync && drop_caches`).
   - **Smart Remediation:** If free RAM drops below 5%, it identifies the top resource-hogging process (Docker or systemd) and safely restarts it.
   - Configurable whitelists ensure critical services (e.g., `ssh`, `networking`) are never interrupted.

3. **Built-in Enterprise Web Dashboard:**
   - Ultra-lightweight Flask web server running on port `8123`.
   - Responsive dark theme powered by Tailwind CSS.
   - Displays widgets for Network Bandwidth, CPU, RAM, and Disk I/O Wait.
   - Features a "Physical Storage Matrix" to display individual disk performance in real-time with dynamic visual warnings.
   - Terminal-style flight recorder to view system events and autonomous interventions.

### ⚙️ Installation

The project includes an automated script that copies files, installs dependencies (like Flask), and sets up the daemon as a systemd service.

```bash
git clone <repository_url> piguard
cd piguard
sudo ./install.sh
```

The default configuration is written to `/etc/piguard/config.json`. You can edit this file to change remediation thresholds and manage your service/container whitelists.

Once installed, you can access the web dashboard by navigating to:
`http://<YOUR_RASPBERRY_IP>:8123`
