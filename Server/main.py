import socket
import threading
import hashlib
import json
import time
from cryptography.hazmat.primitives.asymmetric import rsa, padding
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.fernet import Fernet
HOST = "127.0.0.1"
PORT = 65432

#TODO offline and online users stored in dictionaries used to store offline messages until available

#note: raddr is the remote public ip you are sending data to. laddr is the public ip that is you.
"""
online list goes in a format like this:
username -> conn, addr
"""
fKey = Fernet.generate_key()
privateKey = rsa.generate_private_key(public_exponent=65537, key_size=2048)
publicKey = privateKey.public_key()
def encryptPublicKey(key, input):
    try:
            input.encode("utf-8")
    except(AttributeError):
            pass
    PK = key.encrypt( #PK for public key
            input,
            padding.OAEP(
                    mgf=padding.MGF1(algorithm=hashes.SHA256()),
                    algorithm=hashes.SHA256(),
                    label=None,
                    ),
    )
    return PK
def decryptPrivateKey(key, input):
    try:
            input.encode("utf-8")
    except(AttributeError):
            pass
    PK = key.decrypt( #PK for private key
            input,
            padding.OAEP(
            mgf=padding.MGF1(algorithm=hashes.SHA256()),
            algorithm=hashes.SHA256(),
            label=None,
            ),
    )
    return PK
publicKeyBytes = publicKey.public_bytes(
    encoding=serialization.Encoding.PEM,
    format=serialization.PublicFormat.SubjectPublicKeyInfo
)

usernameVHashed = hashlib.sha256("username".encode("utf-8")).hexdigest()

onlineVHashed = hashlib.sha256("online".encode("utf-8")).hexdigest() #means online verification that is hashed
#basically one client will send its username to this server then the server
#stores that client as online
with open("users.json", "r", encoding="utf-8") as f:
    jsonUsers = f.read()
users = json.loads(jsonUsers)
userKeys = {}
online = {}
offlineMessages = {}
def writeToUsers():
    with open("users.json", "w", encoding="utf-8") as f:
        f.write(json.dumps(users, indent=4))
def connection(conn, addr):
    with conn:
        print(f"Connected by {addr}")
        while True:
            data = conn.recv(1024)
            data.decode()
            if data and (data.decode() == onlineVHashed):
                conn.sendall(publicKeyBytes)
                clientFKeyEncrypted = conn.recv(256)
                print(len(clientFKeyEncrypted))
                clientFKey = decryptPrivateKey(privateKey, clientFKeyEncrypted)
                referenceCFKey = clientFKey#reference of client fernet key
                print(len(clientFKey))
                clientFKey = Fernet(clientFKey)
                usrnameEncrypted = conn.recv(1024)
                usrname = clientFKey.decrypt(usrnameEncrypted).decode()
                userKeys[usrname] = referenceCFKey
                online[usrname] = conn
                if usrname not in users["users"]:
                    users["users"].append(usrname)
                    writeToUsers()
                print(online)
            elif data and (data.decode() == usernameVHashed):
                conn.sendall("2".encode("utf-8"))
                conn.sendall(publicKeyBytes)
                clientFKeyEncrypted = conn.recv(256)
                clientFKey = decryptPrivateKey(privateKey, clientFKeyEncrypted)
                clientFKey = Fernet(clientFKey)
                CUsernameEnc = conn.recv(1024) #Client Username encrypted
                CUsername = clientFKey.decrypt(CUsernameEnc)
                if CUsername not in users["users"]:
                    conn.sendall("good".encode("utf-8"))
                else:
                    conn.sendall("bad".encode("utf-8"))
            elif data and (data.decode() != onlineVHashed):
                msgEnc = userKeys[usrname]
                print(msgEnc)
                msgEnc = Fernet(msgEnc)
                print(msgEnc)
                msg = msgEnc.decrypt(data.decode())
                msg = json.loads(msg)
                print(msg)
                print("Online:", online)
                toUsr = msg["toUsername"]
                fromUsr = msg["fromUsername"]
                if toUsr in online:
                    toConn = online[toUsr]
                    toConnKey = userKeys[toUsr]
                    toConnKey = Fernet(toConnKey)
                    print(str(toConn) + " heloo")
                    toConn.sendall(toConnKey.encrypt(json.dumps(msg).encode("utf-8")))
                else:
                    offlineMessages[toUsr] = {
                        "fromUsername": fromUsr,
                        "message": msg
                    }
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
