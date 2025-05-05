
import socket
import threading
import time
import base64
import hashlib
import os

PORT = 5000
BUFFER_SIZE = 4096
CHUNK_SIZE = 1024
TTL = 10

devices = {}  # nome -> (ip, port, last_seen)
received_files = {}
lock = threading.Lock()

def send_heartbeat(sock, name):
    while True:
        msg = f"HEARTBEAT {name} {PORT}"
        sock.sendto(msg.encode(), ('<broadcast>', PORT))
        time.sleep(2)

def listen(sock):
    while True:
        try:
            data, addr = sock.recvfrom(BUFFER_SIZE)
            try:
                message = data.decode()
            except UnicodeDecodeError:
                message = data.decode(errors='ignore')
            if message.startswith("HEARTBEAT"):
                _, name, port = message.split()
                with lock:
                    devices[name] = (addr[0], int(port), time.time())
            elif message.startswith("TALK"):
                print(f"[{addr[0]}] {message}")
            elif message.startswith("FILE") or message.startswith("CHUNK") or message.startswith("END"):
                handle_file_transfer(message, addr, sock)
            elif message.startswith("ACK") or message.startswith("NACK"):
                print(f"Recebido: {message}")
        except socket.timeout:
            pass

def remove_inactive():
    while True:
        time.sleep(3)
        with lock:
            now = time.time()
            to_delete = [name for name, (_, _, last_seen) in devices.items() if now - last_seen > TTL]
            for name in to_delete:
                del devices[name]

def send_file(filepath, target_ip, target_port, sock):
    if not os.path.isfile(filepath):
        print("Arquivo não encontrado.")
        return

    filename = os.path.basename(filepath)
    with open(filepath, "rb") as f:
        file_data = f.read()

    file_hash = hashlib.sha256(file_data).hexdigest()
    encoded = base64.b64encode(file_data)
    total_chunks = (len(encoded) + CHUNK_SIZE - 1) // CHUNK_SIZE

    file_msg = f"FILE {filename} {total_chunks} {file_hash}"
    sock.sendto(file_msg.encode(), (target_ip, target_port))

    for seq in range(total_chunks):
        chunk_data = encoded[seq * CHUNK_SIZE : (seq + 1) * CHUNK_SIZE]
        chunk_msg = f"CHUNK {seq} ".encode() + chunk_data
        acked = False
        retries = 3

        while not acked and retries > 0:
            sock.sendto(chunk_msg, (target_ip, target_port))
            try:
                sock.settimeout(2)
                resp, _ = sock.recvfrom(BUFFER_SIZE)
                if resp.decode() == f"ACK {seq}":
                    acked = True
                elif resp.decode() == f"NACK {seq}":
                    retries -= 1
            except socket.timeout:
                retries -= 1

        if not acked:
            print(f"Erro no envio do chunk {seq}.")
            return

    sock.sendto("END".encode(), (target_ip, target_port))
    print("Arquivo enviado.")

def handle_file_transfer(message, addr, sock):
    global received_files

    if message.startswith("FILE "):
        _, filename, total, file_hash = message.split()
        total = int(total)
        received_files[filename] = {"chunks": {}, "total": total, "hash": file_hash, "addr": addr}

    elif message.startswith("CHUNK "):
        parts = message.split(' ', 2)
        seq = int(parts[1])
        data = message[len(f"CHUNK {seq} "):].encode()

        for filename, info in received_files.items():
            if seq not in info["chunks"]:
                info["chunks"][seq] = data
                sock.sendto(f"ACK {seq}".encode(), addr)
                return
        sock.sendto(f"NACK {seq}".encode(), addr)

    elif message.startswith("END"):
        for filename, info in received_files.items():
            if len(info["chunks"]) == info["total"]:
                ordered = b''.join(info["chunks"][i] for i in range(info["total"]))
                decoded = base64.b64decode(ordered)
                calc_hash = hashlib.sha256(decoded).hexdigest()

                if calc_hash == info["hash"]:
                    with open(f"recv_{filename}", "wb") as f:
                        f.write(decoded)
                    print(f"Arquivo '{filename}' recebido com sucesso.")
                else:
                    print("Hash incorreto. Arquivo corrompido.")
            else:
                print(f"Arquivo {filename} incompleto.")
        received_files.clear()

def user_interface(name, sock):
    while True:
        cmd = input("> ")
        if cmd == "list":
            with lock:
                for name, (ip, port, _) in devices.items():
                    print(f"{name} -> {ip}:{port}")
        elif cmd.startswith("talk "):
            try:
                _, target_name, msg = cmd.split(" ", 2)
                with lock:
                    if target_name in devices:
                        ip, port, _ = devices[target_name]
                        full = f"TALK {int(time.time())} {msg}"
                        sock.sendto(full.encode(), (ip, port))
            except ValueError:
                print("Uso: talk <nome> <mensagem>")
        elif cmd.startswith("send "):
            try:
                _, target_name, filepath = cmd.split(" ", 2)
                with lock:
                    if target_name not in devices:
                        print("Dispositivo não encontrado.")
                        continue
                    ip, port, _ = devices[target_name]
                send_file(filepath, ip, port, sock)
            except ValueError:
                print("Uso: send <nome> <caminho_arquivo>")
        else:
            print("Comandos: list, talk <nome> <msg>, send <nome> <arquivo>")

if __name__ == "__main__":
    name = input("Nome do dispositivo: ")

    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
    sock.bind(('', PORT))

    threading.Thread(target=send_heartbeat, args=(sock, name), daemon=True).start()
    threading.Thread(target=listen, args=(sock,), daemon=True).start()
    threading.Thread(target=remove_inactive, daemon=True).start()

    user_interface(name, sock)
