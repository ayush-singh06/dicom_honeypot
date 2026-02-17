
import socket

# Use a high port number that doesn't require admin rights
HOST = '127.0.0.1'  # Standard loopback interface address (localhost)
PORT = 11112        # Port to listen on

print(f"[*] Starting server on {HOST}:{PORT}")

# Create a new socket object.
# AF_INET specifies the address family (IPv4).
# SOCK_STREAM specifies the socket type (TCP).
with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
    # Bind the socket to the address and port.
    s.bind((HOST, PORT))
    
    # Enable the server to accept connections. 
    # The number 1 is the backlog of allowed connections.
    s.listen(1)
    
    print("[*] Server is listening and waiting for a connection...")
    
    # Accept a connection. This is a blocking call, meaning the script
    # will pause here until a client connects.
    # conn is a new socket object usable to send and receive data on the connection.
    # addr is the address bound to the socket on the other end of the connection.
    conn, addr = s.accept()
    
    with conn:
        print(f"[*] Accepted connection from {addr[0]}:{addr[1]}")
        
        # Send a welcome message to the connected client.
        # The 'b' prefix converts the string to bytes, which is required for sending.
        conn.sendall(b'Hello! You have connected to the honeypot.')
        
        print("[*] Welcome message sent. Closing connection.")

print("[*] Server shut down.")
