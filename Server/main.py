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
def recvProtocol(byteString):
    while byteString.find("\n") == -1:
        time.sleep(0.1)
def connection(conn, addr):
    with conn:
        print(f"Connected by {addr}")
        while True:
            data = conn.recv(1024)
            data.decode()
            if data:
                conn.sendall(publicKeyBytes + b"\n")
                clientFKeyEncrypted = conn.recv(1024)
                recvProtocol()
                clientFKey = decryptPrivateKey(public_key, clientFKeyEncrypted)
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
