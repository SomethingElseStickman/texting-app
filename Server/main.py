import socket
import threading
import json
import struct
import base64
from enum import IntEnum
from cryptography.hazmat.primitives.asymmetric import rsa, padding
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.fernet import Fernet
HOST = "127.0.0.1"
PORT = 65432
#online list goes in a format like this:
#username -> conn, addr
class packetTypes(IntEnum):
	MESSAGE = 0
	PUBLICKEY = 1
	PUBLICKEYACK = 2
	SERVERFERNETKEY = 3
	FERNETKEY = 4
	REQCLIENTFERNETKEY = 5
	SENDCLIENTFERNETKEY = 6
	CREATEACC = 7
	REGISTERUSER = 8
	VERIFYUSERINFO = 9
	VERIFYRECIPIENTONLINEMSG = 10
	QUITTING = 11
	SERVERCOMM = 12
	ACK = 13

with open("users.json", "r", encoding="utf-8") as f:
	jsonUsers = f.read()
users = json.loads(jsonUsers)
online = {}
offlineMessages = {}
serverPrivateKey = rsa.generate_private_key(public_exponent=65537, key_size=2048)
serverPublicKey = serverPrivateKey.public_key()
pemServerPublicKey = serverPublicKey.public_bytes(
		encoding=serialization.Encoding.PEM,
		format=serialization.PublicFormat.SubjectPublicKeyInfo
)
genFKeyServer = Fernet.generate_key() #fernet key generated for symmetrical encryption
fKeyServer = Fernet(genFKeyServer) #store the generated fernet key
def writeToUsers():
	with open("users.json", "w", encoding="utf-8") as f:
		f.write(json.dumps(users, indent=4))
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
		
def recvExact(sock, length):
		data = b""
		while len(data)<length:
				chunk = sock.recv(length-len(data))
				if not chunk:
						raise ConnectionError("conn closed :(")
				data+=chunk
		return data

def connection(conn, addr):
	with conn:
		clientPublicKey = None

		print(f"Connected by {addr}")
		localUsr = None
		while True:
			header = recvExact(conn, 5)
			packetType, dataLength = struct.unpack("!BI", header)
			data = recvExact(conn, dataLength)
			decodedData = data.decode()
			if not data:
				break
			if packetType == packetTypes.PUBLICKEY:
				clientPublicKey = serialization.load_pem_public_key(data)
				conn.sendall(struct.pack("!BI", packetTypes.PUBLICKEY, len(pemServerPublicKey))+pemServerPublicKey)
			if packetType == packetTypes.PUBLICKEYACK:
				encryptedFernetKey = encryptPublicKey(clientPublicKey, genFKeyServer)
				conn.sendall(struct.pack("!BI", packetTypes.SERVERFERNETKEY, len(encryptedFernetKey))+encryptedFernetKey)
			if packetType == packetTypes.CREATEACC:
				newAcc = fKeyServer.decrypt(decodedData).decode("utf-8")
				userExists = "False"
				for user in users["users"]:
					if (user == newAcc):
						userExists = "True"

						break
				if userExists == "False":
					print("hi")
				encUserExists = fKeyServer.encrypt(userExists.encode("utf-8"))
				conn.sendall(struct.pack("!BI", packetTypes.ACK, len(encUserExists))+encUserExists)
			if packetType == packetTypes.REGISTERUSER:
				usrOnline = json.loads(fKeyServer.decrypt(decodedData))["fromUsername"]
				localUsr = usrOnline
				online[usrOnline] = [conn, addr]
				print(f"REGISTERED: {usrOnline}")
				interv = 0
				for usr in users["users"]:
					if (usr == usrOnline):
						break
					interv+=1
				if interv == len(users["users"]):
					users["users"].append(localUsr)
					writeToUsers()
					interv = 0
				ackDic = {"fromUsername": None, "toUsername": usrOnline, "message": None, "key": None, "additional": None}
				encACKJSON = fKeyServer.encrypt(json.dumps(ackDic).encode("utf-8"))
				conn.sendall(struct.pack("!BI", packetTypes.ACK, len(encACKJSON))+encACKJSON)
			if packetType == packetTypes.VERIFYUSERINFO:
				usrInfo = json.loads(fKeyServer.decrypt(decodedData).decode())
				requestedUser = usrInfo["additional"]
				print(requestedUser)
				userExists = requestedUser in users["users"]
				print(userExists)
				jsonMsg = json.dumps({"fromUsername": None, "toUsername": localUsr, "message": None, "key": None, "additional": None})
				encryptedMsg = fKeyServer.encrypt(jsonMsg.encode("utf-8"))
				responseType = packetTypes.ACK if userExists else packetTypes.SERVERCOMM
				print(responseType)
				conn.sendall(struct.pack("!BI", responseType, len(encryptedMsg))+encryptedMsg)
			if packetType == packetTypes.VERIFYRECIPIENTONLINEMSG:
				recipient = json.loads(fKeyServer.decrypt(decodedData))["toUsername"]
				usrOnline = "False"
				for usr in online:
					if usr == recipient:
						usrOnline = "True"
						break
				jsonResponse = json.dumps({"fromUsername": None, "toUsername": None, "message": None, "key": None, "additional": usrOnline})
				encJSONRESP = fKeyServer.encrypt(jsonResponse.encode("utf-8"))
				conn.sendall(struct.pack("!BI", packetTypes.ACK, len(encJSONRESP))+encJSONRESP)
			if packetType == packetTypes.REQCLIENTFERNETKEY:
				clientReq = json.loads(fKeyServer.decrypt(decodedData))
				restructuredReq = fKeyServer.encrypt(json.dumps(clientReq).encode("utf-8"))
				recipientUsr = clientReq["toUsername"]
				online[recipientUsr][0].sendall(struct.pack("!BI", packetTypes.REQCLIENTFERNETKEY, len(restructuredReq))+restructuredReq)
			if packetType == packetTypes.SENDCLIENTFERNETKEY:
				loadedRslt = json.loads(fKeyServer.decrypt(decodedData))
				restructuredRslt = fKeyServer.encrypt(json.dumps(loadedRslt).encode("utf-8"))
				clientUsr = loadedRslt["toUsername"]
				print("Key response received")
				print("Connection username:", localUsr)
				print("Response sender:", loadedRslt["fromUsername"])
				print("Response recipient:", loadedRslt["toUsername"])
				print("Registered users:", list(online.keys()))
				online[clientUsr][0].sendall(struct.pack("!BI", packetTypes.SENDCLIENTFERNETKEY, len(restructuredRslt))+restructuredRslt)
			if packetType == packetTypes.MESSAGE:
				loadedRslt = json.loads(fKeyServer.decrypt(decodedData))
				print("decoded data ", decodedData)
				print("decrypted data", json.loads(fKeyServer.decrypt(decodedData)))
				restructuredRslt = fKeyServer.encrypt(json.dumps(loadedRslt).encode("utf-8"))
				online[loadedRslt["toUsername"]][0].sendall(struct.pack("!BI", packetTypes.MESSAGE, len(restructuredRslt))+restructuredRslt)
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
