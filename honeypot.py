import logging
import numpy as np
import sys
import datetime
import json
import requests
import threading
import time
import winsound # Windows-specific sound library

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
def security_log(event, message, action_type="unknown"):
    """Robustly logs attacker activity as enriched JSON and plays audio alerts."""
    try:
        # --- Audio Alerts (Windows Beeps) ---
        if action_type == "scan":
            winsound.Beep(440, 400) 
        elif action_type == "query":
            winsound.Beep(600, 600)
        elif "exfiltration" in action_type:
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

        geo = get_geo_info(peer_ip)

        log_data = {
            "timestamp": datetime.datetime.now().isoformat(),
            "node_id": NODE_NAME,
            "attacker_ip": peer_ip,
            "attacker_port": peer_port,
            "attacker_ae_title": attacker_ae,
            "action": action_type,
            "details": message,
            "location": geo,
            "protocol": "dicom"
        }
        
        json_string = json.dumps(log_data)
        with open(LOG_FILE, "a") as f:
            f.write(json_string + "\n")
        
        print(f"[*] [SECURITY EVENT] {message}")

        if ENABLE_SIEM_STREAMING:
            threading.Thread(target=send_to_siem, args=(log_data,), daemon=True).start()
    except Exception as e:
        print(f"[!] Logger Error: {e}")

# --- Fake Database ---
FAKE_PATIENTS = {
    "JH87654": {
        "PatientName": "Javier^Hernandez",
        "PatientID": "JH87654",
        "PatientSex": "M",
        "PatientBirthDate": "19880101",
    }
}

FAKE_STUDIES = {
    "1.2.826.0.1.3680043.10.1.1.20260217.1": {
        "PatientID": "JH87654",
        "StudyDate": "20260217",
        "StudyTime": "103000",
        "StudyDescription": "Fake Brain MRI",
        "StudyInstanceUID": "1.2.826.0.1.3680043.10.1.1.20260217.1",
        "SeriesInstanceUID": "1.2.826.0.1.3680043.10.1.1.20260217.1.1",
        "SOPInstanceUID": "1.2.826.0.1.3680043.10.1.1.20260217.1.1.1",
        "Modality": "MR",
        "StudyID": "MRBRAIN001",
        "AccessionNumber": "",
        "ReferringPhysicianName": "",
    }
}

def generate_fake_image(study_uid):
    """Generates a fake DICOM image dataset."""
    study_info = FAKE_STUDIES[study_uid]
    patient_info = FAKE_PATIENTS[study_info["PatientID"]]

    ds = Dataset()
    ds.file_meta = FileMetaDataset()
    ds.file_meta.MediaStorageSOPClassUID = CTImageStorage
    ds.file_meta.MediaStorageSOPInstanceUID = f"{study_uid}.999"
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
    security_log(event, "Initial Scan (C-ECHO)", action_type="scan")
    return 0x0000

def handle_find(event):
    query = event.identifier
    search_term = getattr(query, 'PatientName', 'All Patients')
    security_log(event, f"Database Query (C-FIND) for: {search_term}", action_type="query")
    
    for study_uid, study_data in FAKE_STUDIES.items():
        ds = Dataset()
        ds.update(FAKE_PATIENTS[study_data["PatientID"]])
        ds.update(study_data)
        yield (0xFF00, ds)
    return 0x0000

def handle_move(event):
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

handlers = [
    (evt.EVT_C_ECHO, handle_echo),
    (evt.EVT_C_FIND, handle_find),
    (evt.EVT_C_MOVE, handle_move)
]

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
