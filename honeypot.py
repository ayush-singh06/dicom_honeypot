import logging
import numpy as np
import sys
import datetime
import json
import requests
import threading
import time
import winsound # Windows-specific sound library
from faker import Faker
import random
import uuid
from pydicom.data import get_testdata_file
from pydicom import dcmread
# --- CONFIGURATION ---
LOG_FILE = "attacks.log"
HONEYPOT_AET = b"HONEYPOTAE"
LISTEN_IP = "0.0.0.0" 
LISTEN_PORT = 11112
STORES_PORT = 11113 
NODE_NAME = "Honeypot-Alpha"

# --- SIEM CONFIGURATION (Loki) ---
SIEM_URL = "http://127.0.0.1:3100/loki/api/v1/push" 
ENABLE_SIEM_STREAMING = True 

# --- ML DATASET & WEBHOOK CONFIG ---
IP_TRACKER = {} # Tracks {ip: last_timestamp} to calculate query speed
DISCORD_WEBHOOK_URL = "https://discord.com/api/webhooks/1503130796159143936/5naKulkjUo5Hzav6ufDXJrMN6XZ2qyPh9WoLUrEScNGoS7UzPTMEMq5NgidV2ZQFCOM_" # Put your webhook here

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.FileHandler(LOG_FILE),
        logging.StreamHandler(sys.stdout)
    ]
)
logging.getLogger('pynetdicom').setLevel(logging.ERROR)

from pynetdicom import AE, evt, AllStoragePresentationContexts
from pynetdicom.sop_class import (
    Verification, 
    StudyRootQueryRetrieveInformationModelFind, 
    PatientRootQueryRetrieveInformationModelFind,
    StudyRootQueryRetrieveInformationModelMove,
    CTImageStorage
)
from pydicom.dataset import Dataset, FileMetaDataset
from pydicom.uid import ImplicitVRLittleEndian, ExplicitVRLittleEndian, ExplicitVRBigEndian

def send_to_siem(payload):
    """Sends logs to Grafana Loki in the required 'streams' format."""
    try:
        curr_time_nano = str(int(time.time() * 1e9))
        loki_payload = {
            "streams": [
                {
                    "stream": {
                        "node_id": payload["node_id"],
                        "action": payload["action"],
                        "attacker_ip": payload["attacker_ip"],
                        "protocol": payload["protocol"]
                    },
                    "values": [
                        [curr_time_nano, json.dumps(payload)]
                    ]
                }
            ]
        }
        headers = {'Content-Type': 'application/json'}
        response = requests.post(SIEM_URL, data=json.dumps(loki_payload), headers=headers, timeout=3)
    except:
        pass

def get_geo_info(ip):
    """Enriches the attack data with geographical location."""
    if ip in ["127.0.0.1", "localhost", "0.0.0.0"]:
        return {"city": "Local Lab", "country": "Internal", "lat": 0, "lon": 0}
    try:
        response = requests.get(f"http://ip-api.com/json/{ip}", timeout=2)
        data = response.json()
        if data.get('status') == 'success':
            return {
                "city": data.get("city", "Unknown"),
                "country": data.get("country", "Unknown"),
                "lat": data.get("lat", 0),
                "lon": data.get("lon", 0)
            }
    except:
        pass
    return {"city": "Unknown", "country": "Unknown", "lat": 0, "lon": 0}

# --- SECURITY LOGGER ---
def security_log(event, message, action_type="unknown", extra_ml_data=None):
    """Robustly logs attacker activity as enriched JSON and plays audio alerts."""
    try:
        # --- Audio Alerts (Windows Beeps) ---
        if action_type == "scan":
            winsound.Beep(440, 400) 
        elif action_type == "query":
            winsound.Beep(600, 600)
        elif "exfiltration_attempt" in action_type:
            def alarm():
                for _ in range(3):
                    winsound.Beep(1000, 150)
                    time.sleep(0.05)
            threading.Thread(target=alarm, daemon=True).start()

        assoc = event.assoc
        
        # Safe extraction of Attacker Info
        requestor = getattr(assoc, 'requestor', None)
        attacker_ae = "UNKNOWN"
        peer_ip = "127.0.0.1"
        peer_port = 0

        if requestor:
            # Get AE Title
            ae_title = getattr(requestor, 'ae_title', b"UNKNOWN")
            if isinstance(ae_title, bytes):
                attacker_ae = ae_title.decode().strip()
            else:
                attacker_ae = str(ae_title).strip()
            
            # Get IP/Port
            addr = getattr(requestor, 'address', ("127.0.0.1", 0))
            peer_ip = addr if isinstance(addr, str) else addr[0]
            peer_port = 0 if isinstance(addr, str) else addr[1]

        # [MACHINE LEARNING METRICS]
        # Calculate exactly how fast this IP is sending requests. 
        # Humans take >1000ms. Automated scripts take <100ms.
        current_time = time.time()
        time_since_last_req_ms = 0
        if peer_ip in IP_TRACKER:
            time_since_last_req_ms = round((current_time - IP_TRACKER[peer_ip]) * 1000, 2)
        IP_TRACKER[peer_ip] = current_time

        # [ATTACKER FINGERPRINTING]
        # Safely extract DICOM presentation contexts. Nmap, real scanners, and APT
        # scripts all request different contexts. We track this for the ML model.
        contexts = []
        if hasattr(assoc, 'accepted_contexts'):
            contexts = [str(ctx.abstract_syntax) for ctx in assoc.accepted_contexts]

        geo = get_geo_info(peer_ip)

        log_data = {
            "timestamp": datetime.datetime.now().isoformat(),
            "node_id": NODE_NAME,
            "attacker_ip": peer_ip,
            "attacker_port": peer_port,
            "attacker_ae_title": attacker_ae,
            "action": action_type,
            "details": message,
            "time_since_last_req_ms": time_since_last_req_ms, # Crucial for ML
            "requested_contexts": contexts, # Fingerprinting dialect
            "location": geo,
            "protocol": "dicom"
        }
        
        if extra_ml_data:
            log_data.update(extra_ml_data)
            
        json_string = json.dumps(log_data)
        with open(LOG_FILE, "a") as f:
            f.write(json_string + "\n")
        
        print(f"[*] [SECURITY EVENT] {message} (Delay: {time_since_last_req_ms}ms)")

        # [INCIDENT RESPONSE / REAL-TIME ALERTS]
        # If the attacker is trying to steal data, instantly fire off an HTTP POST
        # request to the Discord Webhook to ping our mobile phones.
        if action_type == "exfiltration_attempt" and DISCORD_WEBHOOK_URL != "YOUR_DISCORD_WEBHOOK_URL_HERE":
            def send_discord():
                payload = {
                    "content": f"🚨 **CRITICAL ALERT: Data Theft Attempt!**\n**Node:** `{NODE_NAME}`\n**Attacker IP:** `{peer_ip}` ({geo['city']}, {geo['country']})\n**Details:** {message}"
                }
                try:
                    requests.post(DISCORD_WEBHOOK_URL, json=payload, timeout=3)
                except: pass
            threading.Thread(target=send_discord, daemon=True).start()

        if ENABLE_SIEM_STREAMING:
            threading.Thread(target=send_to_siem, args=(log_data,), daemon=True).start()
    except Exception as e:
        print(f"[!] Logger Error: {e}")

# [DECEPTION ENGINE: PROCEDURAL DATA]
# We use the Faker library to mathematically generate realistic patient profiles
# so that the honeypot looks completely real if the hacker inspects the database.
fake = Faker()
FAKE_PATIENTS = {}
FAKE_STUDIES = {}

print("[*] Generating realistic patient database...")
for _ in range(100): # Generate 100 realistic patients
    patient_id = fake.unique.bothify(text='MR-######')
    sex = random.choice(['M', 'F'])
    first_name = fake.first_name_male() if sex == 'M' else fake.first_name_female()
    last_name = fake.last_name()
    
    FAKE_PATIENTS[patient_id] = {
        "PatientName": f"{last_name}^{first_name}",
        "PatientID": patient_id,
        "PatientSex": sex,
        "PatientBirthDate": fake.date_of_birth(minimum_age=18, maximum_age=90).strftime("%Y%m%d"),
    }
    
    # Generate 1-3 studies for each patient
    for _ in range(random.randint(1, 3)):
        study_uid = f"1.2.826.0.1.3680043.10.1.1.{uuid.uuid4().int >> 64}"
        FAKE_STUDIES[study_uid] = {
            "PatientID": patient_id,
            "StudyDate": fake.date_between(start_date='-5y', end_date='today').strftime("%Y%m%d"),
            "StudyTime": fake.time("%H%M%S"),
            "StudyDescription": random.choice(["Brain MRI", "Chest CT", "Pelvis X-Ray", "Spine MRI", "Abdomen CT"]),
            "StudyInstanceUID": study_uid,
            "SeriesInstanceUID": f"{study_uid}.1",
            "SOPInstanceUID": f"{study_uid}.1.1",
            "Modality": random.choice(["MR", "CT", "CR"]),
            "StudyID": fake.bothify(text='ST-####'),
            "AccessionNumber": fake.bothify(text='ACC-########'),
            "ReferringPhysicianName": f"Dr. {fake.last_name()}",
        }
print(f"[*] Generated {len(FAKE_PATIENTS)} patients and {len(FAKE_STUDIES)} studies.")

def generate_fake_image(study_uid):
    """
    [DECEPTION ENGINE: DYNAMIC WATERMARKING]
    Loads a real anonymized sample DICOM image and quietly replaces its internal 
    metadata with our fake generated patient data before feeding it to the attacker.
    """
    study_info = FAKE_STUDIES[study_uid]
    patient_info = FAKE_PATIENTS[study_info["PatientID"]]

    try:
        # Load a real sample DICOM file from pydicom's test dataset
        filename = get_testdata_file("CT_small.dcm")
        if not filename:
            raise Exception("No sample data found in pydicom.")
            
        ds = dcmread(filename)
        
        # Override the sample's metadata with our generated fake data
        ds.update(patient_info)
        ds.update(study_info)
        
        # Ensure the unique identifiers match what the attacker requested
        ds.file_meta.MediaStorageSOPInstanceUID = study_info["SOPInstanceUID"]
        ds.SOPInstanceUID = study_info["SOPInstanceUID"]
        
        # Remove any actual patient identifying info that might have been in the sample
        if 'InstitutionName' in ds:
            ds.InstitutionName = "General Hospital Honeypot"
            
        return ds

    except Exception as e:
        print(f"[!] Error loading real sample DICOM, creating dummy... ({e})")
        # Fallback to generating a dummy if the real file fails to load
        ds = Dataset()
        ds.file_meta = FileMetaDataset()
        ds.file_meta.MediaStorageSOPClassUID = CTImageStorage
        ds.file_meta.MediaStorageSOPInstanceUID = study_info["SOPInstanceUID"]
        ds.file_meta.TransferSyntaxUID = ImplicitVRLittleEndian

        ds.update(patient_info)
        ds.update(study_info)
        ds.SOPClassUID = CTImageStorage
        ds.SOPInstanceUID = ds.file_meta.MediaStorageSOPInstanceUID
        ds.Modality = 'CT'
        ds.Rows = 512
        ds.Columns = 512
        ds.BitsAllocated = 16
        ds.BitsStored = 16
        ds.HighBit = 15
        ds.PixelRepresentation = 0
        ds.SamplesPerPixel = 1
        ds.PhotometricInterpretation = "MONOCHROME2"

        pixel_array = np.zeros((512, 512), dtype=np.uint16)
        for i in range(512):
            pixel_array[i, i] = 65535
            pixel_array[i, 511 - i] = 65535
            
        ds.PixelData = pixel_array.tobytes()
        return ds

# --- Event Handlers ---

def handle_echo(event):
    """
    [DICOM HANDLER: RECONNAISSANCE]
    Triggered when an attacker pings the server (C-ECHO). We log the ping but 
    return 0x0000 (Success) to lure the attacker into thinking the port is vulnerable.
    """
    security_log(event, "Initial Scan (C-ECHO)", action_type="scan")
    return 0x0000

def handle_find(event):
    """
    [DICOM HANDLER: DATABASE ENUMERATION]
    Triggered when an attacker searches for patient data (C-FIND). 
    Instead of returning a real database, we yield the procedural Faker database.
    """
    query = event.identifier
    search_term = getattr(query, 'PatientName', 'All Patients')
    
    extra = {
        "search_term": str(search_term),
        "query_attributes_count": len(query.keys()) if hasattr(query, 'keys') else 0
    }
    security_log(event, f"Database Query (C-FIND) for: {search_term}", action_type="query", extra_ml_data=extra)
    
    for study_uid, study_data in FAKE_STUDIES.items():
        ds = Dataset()
        ds.update(FAKE_PATIENTS[study_data["PatientID"]])
        ds.update(study_data)
        yield (0xFF00, ds)
    return 0x0000

def handle_move(event):
    """
    [DICOM HANDLER: DATA EXFILTRATION]
    Triggered when an attacker tries to steal/download a scan (C-MOVE).
    This is where the trap closes: we generate the fake 16-bit CT scan and feed it to them.
    """
    # CRITICAL: Address MUST be yielded immediately to avoid 0xA801
    yield ('127.0.0.1', STORES_PORT)
    yield 1 
    
    try:
        dest = event.move_destination
        if isinstance(dest, bytes):
            dest = dest.decode().strip()
        
        ds = event.identifier
        study_uid = getattr(ds, 'StudyInstanceUID', 'UNKNOWN')
        
        security_log(event, f"Data Theft Attempt (C-MOVE) for Study: {study_uid} to Destination: {dest}", action_type="exfiltration_attempt")
        
        if study_uid not in FAKE_STUDIES:
            yield (0xA700, None)
            return

        fake_image = generate_fake_image(study_uid)
        yield (0xFF00, fake_image)
        security_log(event, f"SUCCESS: Sent fake image to attacker.", action_type="exfiltration_success")

    except Exception as e:
        # We don't call security_log here to avoid infinite recursion if it's the cause
        print(f"[!] Error in handle_move: {e}")
        yield (0xA702, None)

# --- Main Server Setup ---

# Map the DICOM commands to our Python trap functions
handlers = [
    (evt.EVT_C_ECHO, handle_echo),
    (evt.EVT_C_FIND, handle_find),
    (evt.EVT_C_MOVE, handle_move)
]

# [SERVER INITIALIZATION]
# Create the Application Entity (AE) which acts as the fake hospital server.
ae = AE(ae_title=HONEYPOT_AET)
ae.supported_contexts = AllStoragePresentationContexts
ae.add_supported_context(Verification)
ae.add_supported_context(PatientRootQueryRetrieveInformationModelFind)
ae.add_supported_context(StudyRootQueryRetrieveInformationModelFind)
ae.add_supported_context(StudyRootQueryRetrieveInformationModelMove)
ae.add_requested_context(CTImageStorage)

print(f"[*] DICOM Honeypot active on {LISTEN_IP}:{LISTEN_PORT}")
print(f"[*] Logging attacks to {LOG_FILE} and streaming to SIEM...")
ae.start_server((LISTEN_IP, LISTEN_PORT), evt_handlers=handlers)
