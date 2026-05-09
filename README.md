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
*   **Deception Engine:** Uses **NumPy** for procedural generation of 512x512 pixel arrays, creating structurally valid but biologically fake DICOM files.
*   **Audio Intelligence:** Uses Windows `winsound` to provide real-time auditory feedback on threat levels (Scanning vs. Exfiltration).

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

To demonstrate the system's effectiveness, open a new terminal and simulate a hacker's lifecycle:

### Stage 1: Reconnaissance (Scan)
Hackers scan for open medical devices.
```bash
echoscu -v 127.0.0.1 11112
```
*Result: Short beep. "Scan" entry appears in Grafana.*

### Stage 2: Enumeration (Browse)
Hackers search the database for high-value patient data.
```bash
findscu -v -S -k 0010,0010="" 127.0.0.1 11112
```
*Result: Medium beep. Logs "Wildcard Search" in the SIEM.*

### Stage 3: Exfiltration (Theft)
Hackers attempt to download the medical images.
1. **Start Hacker's Receiver:** `storescp -v 11113 -od received_images`
2. **Execute Theft:** 
   ```bash
   movescu -v -S -aem STORESCP -aec HONEYPOTAE 127.0.0.1 11112 -k StudyInstanceUID=1.2.826.0.1.3680043.10.1.1.20260217.1
   ```
*Result: 🚨 Triple-beep alarm! A fake image is generated and sent to the hacker's server.*

---

## 📁 Project Structure
```text
├── honeypot.py         # Main Sensor logic & Data Deception engine
├── docker-compose.yml  # SIEM Infrastructure orchestration (Loki/Grafana)
├── requirements.txt    # Python dependencies
├── README.md           # Professional documentation
└── received_images/    # Forensic folder for exfiltrated trap data
```

---

## 🧠 Future Roadmap
*   **Web Dashboard:** Hosting Grafana on Oracle Cloud for public viewing.
*   **Alerting:** Integration with Discord/Slack for real-time mobile push notifications of attacks.
*   **Machine Learning:** Training a model on attack logs to predict future medical data breaches.

---

Do not use on production networks without authorization.

---
*Developed as a Major Project to bridge the gap between Healthcare Informatics and Cybersecurity.*
