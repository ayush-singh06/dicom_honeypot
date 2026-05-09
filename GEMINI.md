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

### Step 2: Creating "Fake Data" (Numpy)
We used the `numpy` library to generate a 512x512 array of random numbers. 
*   *Why:* Real DICOM files are huge. Instead of storing 1,000 real images (which is illegal/private), we **mathematically generate** a fake image the instant a hacker tries to steal one. This is "Procedural Generation."

### Step 3: Structured Logging (JSON)
We changed the logs from "Plain Text" to "JSON." 
*   *Why:* Databases like Loki cannot "read" human sentences easily. JSON turns `[Attacker 127.0.0.1 scanned]` into `{"attacker_ip": "127.0.0.1", "action": "scan"}`. This allows us to filter data by "Action" later in Grafana.

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

1.  **Attacker** runs `movescu` (The Theft).
2.  **Honeypot** receives the request and triggers `handle_move`.
3.  **Honeypot** immediately starts a **Thread** to play an alarm beep.
4.  **Honeypot** sends the Attacker's IP to an **API** to find their City/Country.
5.  **Honeypot** packs all this info into a **JSON** object.
6.  **Honeypot** sends this JSON to **Loki** over the network.
7.  **Grafana** sees the new data in Loki and draws a **Red Dot** on the map.
8.  **Honeypot** sends a **Fake Image** to the attacker's server (`storescp`) to finish the trap.

---

## 4. 🚀 Demo Command Reference

### Start Order:
1.  **Docker Desktop:** (Must be running).
2.  **SIEM:** `docker-compose up -d`
3.  **Receiver (The Hacker's Safe):** `storescp -v 11113 -od received_images`
4.  **The Trap (Honeypot):** `python honeypot.py` (Run in CMD).

### Attack Commands:
*   **Scan:** `echoscu -v 127.0.0.1 11112`
*   **Browse:** `findscu -v -S -k 0010,0010="" 127.0.0.1 11112`
*   **Steal:** `movescu -v -S -aem STORESCP -aec HONEYPOTAE 127.0.0.1 11112 -k StudyInstanceUID=1.2.826.0.1.3680043.10.1.1.20260217.1`
