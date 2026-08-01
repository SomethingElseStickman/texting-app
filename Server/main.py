import socket
import threading
import hashlib
import json
HOST = "127.0.0.1"
PORT = 65432
#offline and online users stored in dictionaries used to store offline messages until available
"""
online list goes in a format like this:
username -> conn, addr
"""

usernameVHashed = hashlib.sha256("username".encode("utf-8")).hexdigest()

onlineVHashed = hashlib.sha256("online".encode("utf-8")).hexdigest() #means online verification that is hashed
#basically one client will send its username to this server then the server
#stores that client as online
with open("users.json", "r", encoding="utf-8") as f:
    jsonUsers = f.read()
users = json.loads(jsonUsers)
online = {}
offline = {}
def writeToUsers():
    with open("users.json", "w", encoding="utf-8") as f:
        f.write(json.dumps(users, indent=4))
def connection(conn, addr):
    with conn:
        print(f"Connected by {addr}")
        while True:
            data = conn.recv(1024)
            if data and (data.decode() == onlineVHashed):
                conn.sendall("1".encode("utf-8"))
                usrname = conn.recv(1024)
                online[usrname.decode()] = [conn, addr]
                if usrname not in users["users"]:
                    users["users"].append(usrname.decode())
                    writeToUsers()
                print(online)
            elif data and (data.decode() == usernameVHashed):
                conn.sendall("2".encode("utf-8"))
                CUsername = conn.recv(1024).decode() #Client Username
                if ((CUsername not in online) and (CUsername not in offline)) or (CUsername not in users["users"]):
                    conn.sendall("good".encode("utf-8"))
                else:
                    conn.sendall("bad".encode("utf-8"))
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
