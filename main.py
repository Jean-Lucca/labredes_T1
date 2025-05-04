import socket
import threading
import time
from datetime import datetime, timedelta

# Configuration
BROADCAST_IP = "255.255.255.255"  # Broadcast address for the lab network
PORT = 8080                       # Port used by all containers (mapped to 8080, 8081, etc. on host)
DEVICE_NAME = "device2"           # Unique name for this device (set dynamically or via config)
BROADCAST_INTERVAL = 5            # Send HEARTBEAT every 5 seconds
TIMEOUT = 10                      # Remove devices inactive for 10 seconds

# Shared device list (thread-safe)
devices = {}  # {device_name: {"ip": str, "port": int, "last_heartbeat": datetime}}
devices_lock = threading.Lock()

def send_heartbeat():
    """Send HEARTBEAT messages every 5 seconds via UDP broadcast."""
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    
    while True:
        message = f"HEARTBEAT {DEVICE_NAME}"
        try:
            sock.sendto(message.encode(), (BROADCAST_IP, PORT))
            print(f"Sent: {message}")
        except Exception as e:
            print(f"Error sending HEARTBEAT: {e}")
        time.sleep(BROADCAST_INTERVAL)

def receive_heartbeat():
    """Receive HEARTBEAT messages and update the device list."""
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    sock.bind(("", PORT))  # Bind to all interfaces on PORT
    
    while True:
        try:
            data, (ip, port) = sock.recvfrom(1024)
            message = data.decode().strip()
            if message.startswith("HEARTBEAT "):
                device_name = message.split(" ", 1)[1]
                with devices_lock:
                    devices[device_name] = {
                        "ip": ip,
                        "port": port,
                        "last_heartbeat": datetime.now()
                    }
                print(f"Received: {message} from {ip}:{port}")
        except Exception as e:
            print(f"Error receiving HEARTBEAT: {e}")

def cleanup_inactive_devices():
    """Remove devices that haven't sent a HEARTBEAT in 10 seconds."""
    while True:
        with devices_lock:
            current_time = datetime.now()
            inactive_devices = [
                name for name, info in devices.items()
                if (current_time - info["last_heartbeat"]).total_seconds() > TIMEOUT
            ]
            for name in inactive_devices:
                del devices[name]
                print(f"Removed inactive device: {name}")
        time.sleep(1)  # Check every second

def print_devices():
    """Print the current list of active devices."""
    with devices_lock:
        if not devices:
            print("No active devices.")
        for name, info in devices.items():
            time_since_last = (datetime.now() - info["last_heartbeat"]).total_seconds()
            print(f"Device: {name}, IP: {info['ip']}, Port: {info['port']}, "
                  f"Last HEARTBEAT: {time_since_last:.1f}s ago")

def main():
    # Start threads for sending, receiving, and cleaning up
    threading.Thread(target=send_heartbeat, daemon=True).start()
    threading.Thread(target=receive_heartbeat, daemon=True).start()
    threading.Thread(target=cleanup_inactive_devices, daemon=True).start()

    # Simple CLI for testing
    while True:
        command = input("Enter command (devices/quit): ").strip().lower()
        if command == "devices":
            print_devices()
        elif command == "quit":
            break

if __name__ == "__main__":
    # Set a unique device name (e.g., based on container ID or user input)
    import sys
    DEVICE_NAME = sys.argv[1] if len(sys.argv) > 1 else DEVICE_NAME
    main()
