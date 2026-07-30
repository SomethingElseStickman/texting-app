import socket
import threading
import hashlib
HOST = "127.0.0.1"
PORT = 65432
#offline and online users stored in dictionaries used to store offline messages until available
"""
online list goes in a format like this:
username -> conn, addr
"""

onlineVHashed = hashlib.sha256("online".encode("utf-8")).hexdigest() #means online verification that is hashed

online = {}
offline = {}
#basically one client will send its username to this server then the server
#stores that client as online
def connection(conn, addr):
    with conn:
        print(f"Connected by {addr}")
        while True:
            data = conn.recv(1024)
            if data and (data.decode() == onlineVHashed):
                conn.sendall("1".encode("utf-8"))
                usrname = conn.recv(1024)
                online[usrname] = [conn, addr]
                print(online)
            elif data and (data.decode() != onlineVHashed):
                conn.sendall(data)
            if not data:
                break

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
