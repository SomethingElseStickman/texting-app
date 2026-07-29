import socket
import threading

HOST = "127.0.0.1"
PORT = 65432

def connection(conn, addr):
    with conn:
        print(f"Connected by {addr}")

        while True:
            data = conn.recv(1024)

            if not data:
                break

            conn.sendall(data)

def listen(server):
    server.bind((HOST, PORT))
    server.listen()

    while True:
        conn, addr = server.accept()

        t = threading.Thread(
            target=connection,
            args=(conn, addr),
            daemon=True
        )

        t.start()

with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as server:
    listen(server)
