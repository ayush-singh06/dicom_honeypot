# 🏥 DICOMTRAP: High-Interaction Medical Honeynet & SIEM

**DICOMTRAP** is an advanced cyber-deception platform that emulates a vulnerable Medical Imaging Server (PACS). It is designed to attract, engage, and analyze attackers targeting healthcare infrastructure, providing a scalable, distributed solution for real-time threat intelligence.

---

## 📽️ Project Demonstration

Imagine a hospital network under attack. A hacker scans the network, finds an open DICOM port, and attempts to steal sensitive patient MRIs. **DICOMTRAP** intercepts this:
1.  **Lures:** Responds to scans as if it were a real GE or Siemens imaging server.
2.  **Engages:** Returns fake patient records to the hacker's queries.
3.  **Traps:** Procedurally generates a fake 16-bit medical image on-the-fly and "feeds" it to the hacker.
4.  **Enriches:** Simultaneously tracks the hacker's IP, physical location, and technique, visualizing it on a global SIEM dashboard.

---

## 🛠️ Technology Deep Dive

### 1. The Sensor (Honeypot Node)
*   **Protocol:** Implements the full DICOM network handshake using `pynetdicom`.
*   **Deception Engine:** Uses the `Faker` library to procedurally generate hundreds of realistic patient records on the fly, and injects them into real anonymized medical scans (`pydicom` test data) to create structurally valid but completely fake DICOM files.
*   **Audio Intelligence:** Uses Windows `winsound` to provide real-time auditory feedback on threat levels (Scanning vs. Exfiltration).
*   **High-Resolution ML Logging:** Tracks micro-behaviors (query speed, specific search terms, requested DICOM presentation contexts) to build a dataset for future Machine Learning profiling.
*   **Incident Response:** Features a Discord Webhook integration for instant mobile push notifications when an attack occurs.

### 2. The SIEM Pipeline (PLG Stack)
*   **Loki:** A high-efficiency log aggregation system that receives structured JSON logs via an asynchronous multi-threaded pipeline.
*   **Grafana:** A modern visualization suite configured with:
    *   **Geomap:** Plotting physical attack origins using Geo-IP enrichment.
    *   **Attack Lifecycle Table:** A forensic breakdown of every DIMSE (C-ECHO, C-FIND, C-MOVE) command sent by the attacker.
    *   **Threat Gauges:** Visualizing current attack pressure.

---

## 🚀 Installation & Setup

### Prerequisites
*   Windows 10/11 (for audio features)
*   [Docker Desktop](https://www.docker.com/products/docker-desktop/)
*   Python 3.10+

### Step 1: Clone and Install
```bash
git clone https://github.com/your-username/dicom-honeypot.git
cd dicom-honeypot
pip install -r requirements.txt
```

### Step 2: Launch the Infrastructure
Start the central SIEM brain (Loki & Grafana):
```bash
docker-compose up -d
```
Verify they are running at `http://localhost:3000` (User: `admin`, Pass: `admin`).

### Step 3: Start the Honeypot Sensor
Open a **Command Prompt (CMD)** window (required for system beeps) and run:
```cmd
python honeypot.py
```

---

## 🧪 Running a Simulated Attack (The Demo)

To demonstrate the system's effectiveness and massive scale, we use a custom Advanced Persistent Threat (APT) simulation script.

### Step 1: Start the Attack Simulator
Open a new terminal and run:
```bash
python attacker_simulation.py
```

### The 3-Stage Attack Lifecycle:
1. **Reconnaissance (Scan):** The script sends a `C-ECHO` to ping the honeypot.
   *Result: Short beep. Honeypot logs the scanner's digital fingerprint (requested_contexts) for future ML profiling.*
2. **Enumeration (Browse):** The script executes a wildcard (`*`) `C-FIND` query, dumping the entire generated database of 100+ fake patients to the attacker's screen.
   *Result: Medium beep. ML Logger records the query speed and wildcard search.*
3. **Exfiltration (Theft):** The script launches a built-in storage server and sends a `C-MOVE` command to automatically steal the high-value medical scans.
   *Result: 🚨 Triple-beep alarm! A Discord Push Notification is instantly sent to your phone. Fake CT scans are dynamically generated, injected with fake names, and downloaded to the `received_images/` folder on the attacker's machine.*

---

## 📁 Project Structure
```text
├── honeypot.py             # Main Sensor logic, Data Deception, and ML Logging
├── attacker_simulation.py  # Automated 3-stage APT attack script for live demos
├── attacks.log             # High-resolution JSON behavioral dataset for ML
├── docker-compose.yml      # SIEM Infrastructure orchestration (Loki/Grafana)
├── requirements.txt        # Python dependencies
├── reference_file.md       # Personal technical cheat sheet and roadmap
├── README.md               # Professional documentation
└── received_images/        # Forensic folder where stolen trap files are saved
```

---

Do not use on production networks without authorization.

---
*Developed as a Major Project to bridge the gap between Healthcare Informatics and Cybersecurity.*