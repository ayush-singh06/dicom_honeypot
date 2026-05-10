# 📘 DICOMTRAP: Personal Technical Master Reference

This document explains **exactly** how we built this project, why we chose each technology, and what all the "jargon" means. Use this to prepare for your presentation or to refresh your memory.

---

## 1. 📖 The "Jargon" Dictionary (Terms You Need to Know)

### Medical Protocol (DICOM)
*   **DICOM:** The universal "language" used by medical machines (MRI, CT, X-ray) to talk to each other.
*   **AE Title (Application Entity):** The "Username" of a medical device. Our honeypot is `HONEYPOTAE`.
*   **SCP (Service Class Provider):** The **Server** (our honeypot). It "provides" a service.
*   **SCU (Service Class User):** The **Client** (the attacker). it "uses" a service.
*   **C-ECHO (The Ping):** A simple "Are you there?" request.
*   **C-FIND (The Query):** A search request (e.g., "Give me a list of all patients").
*   **C-MOVE (The Theft):** A request to send a file to a specific destination.
*   **Presentation Context:** A "negotiation" at the start of a connection where both sides agree on what data they can speak (e.g., "I speak MRI images in Little Endian format").

### Security & Data Engineering
*   **Honeypot:** A trap server designed to look like a high-value target (like a hospital server).
*   **SIEM:** Security Information and Event Management. A central "brain" that collects logs from many sources and visualizes them.
*   **PLG Stack:** Our specific SIEM using **P**rometheus (optional), **L**oki (Logs), and **G**rafana (Dashboard).
*   **JSON:** A structured way of writing data so machines can read it easily.
*   **Asynchronous (Threading):** Running two things at once. We use this so the honeypot can play a beep and send data to the database without stopping the DICOM connection.
*   **Geo-IP Enrichment:** Using an IP address to look up a physical location (City/Country) on a map.

---

## 2. 🛠️ The Build Steps (Everything We Did)

### Step 1: Building the "Decoy" (Python + pynetdicom)
We started by writing a Python script that uses `pynetdicom` to listen on port `11112`. We wrote "Handlers"—functions that trigger when a specific command arrives.
*   *Why:* To make the computer act like a real medical device.

### Step 2: Creating "Fake Data" (Faker & Pydicom)
We used the `Faker` library to dynamically generate hundreds of realistic patient names and IDs. We then use `pydicom` to load a real, anonymized CT scan and silently overwrite its internal metadata with our fake patient data. 
*   *Why:* Real DICOM files are huge. Instead of storing thousands of real images (which is illegal/private), we dynamically build a highly-convincing fake image the instant a hacker tries to steal one.

### Step 3: High-Resolution Structured Logging (JSON)
We changed the logs from "Plain Text" to "JSON" and added High-Resolution fields (`time_since_last_req_ms`, `requested_contexts`, `search_term`).
*   *Why:* Databases like Loki cannot "read" human sentences easily. JSON turns `[Attacker 127.0.0.1 scanned]` into `{"attacker_ip": "127.0.0.1", "action": "scan"}`. The extra High-Resolution fields are critical for building a dataset that will train a Machine Learning model next semester to detect automated bots based on query speed and fingerprinting.

### Step 4: Building the "Central Brain" (Docker + Loki)
We used Docker to run **Loki**. 
*   *Loki* is a "Log Aggregator." It has a **Push API**. Our Python script "Pushes" the JSON logs to Loki's URL (`http://localhost:3100`).
*   *Why:* This makes the project **Scalable**. You can have 10 honeypots in different countries all "Pushing" to this one central Loki server.

### Step 5: The Visual Dashboard (Grafana)
We connected Grafana to Loki. We learned how to use **Transformations**:
1.  **Extract Fields:** Pulling the IP and Action out of the JSON string.
2.  **Organize Fields:** Hiding the "rubbish" columns (like ID and tsNs) to make a clean table.
3.  **Geomap:** Pulling the `lat` and `lon` fields to place a red dot on a world map.

### Step 6: Audio Intelligence (Winsound)
We added `winsound.Beep` to the script.
*   *Why:* For a live demo, sound is powerful. It proves the honeypot is "thinking" and "categorizing" threats (Low beep for scans, High alarm for theft).

---

## 3. 🔄 How the Data Flows (The "Story")

1.  **Attacker** runs `attacker_simulation.py`.
2.  **Attacker** sends a `C-MOVE` (The Theft) command.
3.  **Honeypot** receives the request and triggers `handle_move`.
4.  **Honeypot** immediately starts a **Thread** to play an alarm beep and fires an HTTP request to a **Discord Webhook** for a mobile push notification.
5.  **Honeypot** extracts ML behavioral data (query speed, requested contexts) and Geo-IP location.
6.  **Honeypot** packs all this info into a **JSON** object and sends it to **Loki**.
7.  **Grafana** sees the new data in Loki and updates the Threat Dashboards.
8.  **Honeypot** injects fake data into a real CT scan and sends it back to the attacker's local `received_images` folder to finish the trap.

---

## 4. 🚀 Demo Command Reference

### Start Order:
1.  **Docker Desktop:** (Must be running).
2.  **SIEM:** `docker-compose up -d`
3.  **The Trap (Honeypot):** `python honeypot.py` (Run in CMD for audio).

### Attack Simulation:
Open a **second terminal** window and run:
```bash
python attacker_simulation.py
```
*(This automatically runs the C-ECHO scan, C-FIND database dump, starts a local receiver, and executes the C-MOVE theft).*

---

## 5. 🔮 Future Roadmap (7th Semester Extension)

To elevate this project in the next semester, we will implement the following advanced cybersecurity concepts:

### 1. "Radioactive" Honeytokens (DICOM Watermarking)
*   **Concept:** Secretly injecting a unique tracking ID (e.g., `TRACKING-ID: NODE-ALPHA-992`) into an obscure DICOM metadata tag of the fake image before it is sent to the attacker.
*   **Purpose:** If the stolen dataset is ever leaked or sold on the Dark Web, researchers can analyze the file, extract the hidden tag, and mathematically prove exactly which honeypot node it was stolen from and at what exact time.

### 2. The "Tarpit" (Active Network Deception)
*   **Concept:** Instead of sending the fake image to the attacker instantly, the honeypot will intentionally slow down the network connection, transferring the file at a crawling speed (e.g., 1 kilobyte per second).
*   **Purpose:** This wastes the attacker's server resources, traps their automated scanning scripts in a prolonged connection, and buys the hospital's Incident Response team hours to trace the attacker's IP address before they realize they are stuck in a trap.

### 3. Machine Learning & Attacker Profiling
*   **Concept:** Utilizing the high-resolution JSON data gathered during the 6th semester (query speeds, search terms, and `requested_contexts` DICOM dialects) to train a Machine Learning classification model (using Scikit-learn or PyTorch).
*   **Purpose:** The ML model will automatically classify the skill level and type of attacker (e.g., "Automated Nmap Scanner", "Ransomware Bot", or "Advanced Persistent Threat") based purely on their behavioral fingerprint, without relying on traditional IP blocklists.
