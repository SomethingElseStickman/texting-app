import socket
from PyQt5.QtWidgets import (
QApplication, QMainWindow, QLineEdit, QMessageBox, QVBoxLayout, QLabel, 
QHBoxLayout, QScrollArea, QWidget, QDialog, QDialogButtonBox, QComboBox, 
QToolBar, QAction, QSizePolicy
)
from PyQt5.QtGui import QIcon
from PyQt5.QtCore import QSize, Qt, pyqtSignal
import threading
import sys
import json
import hashlib
import os
import time
import struct
import atexit
import base64
from enum import IntEnum
from cryptography.hazmat.primitives.asymmetric import rsa, padding
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.fernet import Fernet
HOST =  "127.0.0.1"
PORT = 65432
noteToSelfUser = "127.0.0.1"

fKeyServer = None
genFKeyClient = Fernet.generate_key()
fKeyClient = Fernet(genFKeyClient)
fKeyRecipient = None
privateKey = rsa.generate_private_key(public_exponent=65537, key_size=2048)
publicKey = privateKey.public_key()
serverPublicKey = None
textedBefore = False
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
pemClientPublicKey = publicKey.public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo
)
clientSock = None
recvData = False
undecodedRecvData = False
recvDataReady = threading.Event()
incomingMsg = threading.Event()
usernameExistsReady = threading.Event()
recvPacketsThreadStarted = False
fileDir = os.path.dirname(__file__)
iconDir = os.path.join(fileDir, "icons")
with open("contacts.json", "r", encoding="utf-8") as f:
        jsonContacts = f.read()
dicContacts = json.loads(jsonContacts)
username = dicContacts["username"]
contacts = []
contactUsernames = []
contactStatuses = []
contactMsgCache = []
contactMsgName = ""
contactUsrName = ""
temp = None
interv = 0
localTxt = None
recvPacketType = None
ackOnlineToServer = False
usernameExists = None
onlineNotifier = 1 #tells send packets func if we are just notifying online status or are sending a text message
#iterates through the contact json script
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
def threadSendPackets(usernameAuth: str, packetType: str, msg="disregard this message - sent by program DISREGARD"):
        th = threading.Thread(
                target=sendPackets,
                args=(usernameAuth, packetType, msg),
                daemon=True
        )
        th.start()
def recvExact(sock, length):
        data = b""
        while len(data)<length:
                chunk = sock.recv(length-len(data))
                if not chunk:
                        raise ConnectionError("conn closed :(")
                data+=chunk
        return data
def iterateThroughContacts():
        global contacts, contactUsernames, contactStatuses
        for contact in dicContacts["contacts"]:
                contacts.append(contact["contact_name"])
                contactUsernames.append(contact["username"])
                contactStatuses.append(contact["status"])
                contactMsgCache.append(contact["msg_cache"])
iterateThroughContacts()
def updateContacts():
        with open("contacts.json", "w", encoding="utf-8") as f:
                f.write(json.dumps(dicContacts, indent=4))
#send packets to the server
#NOTE: right now it just sends the text back to the sender
def checkUsername(tmp: str, addC=False): #tmp for the userauth but im too lazy to make a name for that also addC for addcontact var
        if tmp != noteToSelfUser:
                threadSendPackets(tmp, "verifyUserExists")
        else:
                return True
        """def mainL(): #main logic
                global usernameExists
                usernameExists = None"""
        usernameExistsReady.wait()
        UE = usernameExists
        usernameExistsReady.clear()
        if UE:
                if addC == True: #return for if func is checking if user is in database
                        #mainL()
                        return True #TODO reverse server returning if or if not user is in database.
                else: #return for if func is checking if the user is not in the database
                        #mainL()
                        return False
        else:
                if addC == True:
                        #mainL()
                        return False
                else:
                        #mainL()
                        return True

class addUser(QDialog):
        def __init__(self):
                super().__init__()
                self.setWindowTitle("Add Your Username")
                btns = QDialogButtonBox.Apply | QDialogButtonBox.Close
                self.btnWidget = QDialogButtonBox(btns)
                self.inpLabel = QLabel("Enter In a Username")
                self.inp = QLineEdit()
                btnLayout = QVBoxLayout()
                btnLayout.addWidget(self.inpLabel)
                btnLayout.addWidget(self.inp)
                self.setLayout(btnLayout)

                def returnP():  #return pressed
                        global username
                        userAvailable = checkUsername(self.inp.text())
                        if userAvailable:
                                username = self.inp.text()
                                dicContacts["username"] = username
                                updateContacts()
                                self.accept()
                        else:
                                redoDlg = QMessageBox(self)
                                redoDlg.setWindowTitle("Redo Input")
                                redoDlg.setText("This username is already taken")
                                redoDlg.setStandardButtons(QMessageBox.Retry)
                                redoDlg.setIcon(QMessageBox.Warning)
                                redoDlg.exec()
                                return
                def denied():
                        self.reject()
                self.inp.returnPressed.connect(returnP)
                self.btnWidget.button(QDialogButtonBox.Apply).clicked.connect(returnP)
                self.btnWidget.button(QDialogButtonBox.Close).clicked.connect(denied)
def sendPackets(usernameAuth: str, packetType: str, msg="disregard this message - sent by program DISREGARD"):
        #global onlineNotifier
        global localTxt
        global recvData
        global serverPublicKey
        global ackOnlineToServer
        global usernameExists
        global fKeyRecipient
        global textedBefore
        global fKeyServer
        client = clientSock
        if (packetType == "statusOnlineSend") or ((packetType == "verifyUserExists") and not (ackOnlineToServer)):
                client.sendall(struct.pack("!BI", packetTypes.PUBLICKEY, len(pemClientPublicKey))+pemClientPublicKey)
                recvDataReady.wait()
                result = undecodedRecvData
                recvDataReady.clear()
                serverPublicKey = serialization.load_pem_public_key((result)) #loads server pem key
                result = None
                client.sendall(struct.pack("!BI", packetTypes.PUBLICKEYACK, len("10".encode("utf-8")))+"10".encode("utf-8")) #just a random payload to deliver ack
                recvDataReady.wait()
                result = recvData
                recvDataReady.clear()
                fKeyServer = Fernet(decryptPrivateKey(privateKey, result))
                if (username == "anonymous"):
                        encryptedUserAuth = fKeyServer.encrypt(usernameAuth.encode("utf-8"))
                        client.sendall(struct.pack("!BI", packetTypes.CREATEACC, len(encryptedUserAuth))+encryptedUserAuth)
                        recvDataReady.wait()
                        result = recvData
                        ack = recvPacketType
                        recvDataReady.clear()
                        if (ack != packetTypes.ACK):
                                return
                        if ((fKeyServer.decrypt(result) == "True") or (fKeyServer.decrypt(result) == True)):
                                usernameExists = True
                                return
                        usernameExists = False
                usernameInfo = {"fromUsername": username, "toUsername": None, "message": None, "key": None, "additional": None} #difference
                encryptedUsrInfo = fKeyServer.encrypt(json.dumps(usernameInfo).encode("utf-8"))
                client.sendall(struct.pack("!BI", packetTypes.REGISTERUSER, len(encryptedUsrInfo))+encryptedUsrInfo)
                result = None
                recvDataReady.wait()
                result = recvData
                ack = recvPacketType
                recvDataReady.clear()
                if ack != packetTypes.ACK:
                        print("ack not sent :(")
                        return
                ackOnlineToServer = True #difference
        if (packetType == "verifyUserExists"):
                usernameInfo = {"fromUsername": username, "toUsername": None, "message": None, "key": None, "additional": usernameAuth}
                encryptedUserInfo = fKeyServer.encrypt(json.dumps(usernameInfo).encode("utf-8"))
                client.sendall(struct.pack("!BI", packetTypes.VERIFYUSERINFO, len(encryptedUserInfo))+encryptedUserInfo)
                recvDataReady.wait()
                result = recvData
                ack = recvPacketType
                recvDataReady.clear()
                result = None
                if (ack == packetTypes.ACK):
                        usernameExists = True
                        usernameExistsReady.set()
                        return
                else:
                        usernameExists = False
                        usernameExistsReady.set()
                        return
        if (packetType == "messagingSetup"):
                checkOnline = {"fromUsername": username, "toUsername": contactUsrName, "message": None, "key": None, "additional": None}
                encryptedCheck = fKeyServer.encrypt(json.dumps(checkOnline).encode("utf-8"))
                client.sendall(struct.pack("!BI", packetTypes.VERIFYRECIPIENTONLINEMSG, len(encryptedCheck))+encryptedCheck)
                recvDataReady.wait()
                result = recvData
                recvDataReady.clear()
                decryptedResult = json.loads(fKeyServer.decrypt(result))
                result = None

                if decryptedResult["additional"] != "True":
                        for contact in dicContacts["contacts"]:
                                if contact["username"] == contactUsrName:
                                        contact["status"] = "offline"
                                        contact["msg_cache"] = msg
                                        updateContacts()
                                        break
                        return
                decryptedResult = None
                dictPublicKeyToRecipient = {"fromUsername": username, "toUsername": contactUsrName, "message": None, 
                        "key": base64.b64encode(pemClientPublicKey).decode("utf-8"), "additional": None}
                encryptedPKTR = fKeyServer.encrypt(json.dumps(dictPublicKeyToRecipient).encode("utf-8"))
                client.sendall(struct.pack("!BI", packetTypes.REQCLIENTFERNETKEY, len(encryptedPKTR))+encryptedPKTR)
                recvDataReady.wait()
                result = recvData
                recvDataReady.clear()
                fKeyRecipient = Fernet(decryptPrivateKey(privateKey, base64.b64decode(json.loads(fKeyServer.decrypt(result))["key"])))
                textedBefore = True
        if (packetType == "message"):
                encryptedMsg = fKeyRecipient.encrypt(msg.encode("utf-8"))
                dictMsg = {"fromUsername": username, "toUsername": contactUsrName, "message": base64.b64encode(encryptedMsg).decode("utf-8"), "key": None, "additional": None}
                encryptedDictMsg = fKeyServer.encrypt(json.dumps(dictMsg).encode("utf-8"))
                client.sendall(struct.pack("!BI", packetTypes.MESSAGE, len(encryptedDictMsg))+encryptedDictMsg)
                recvDataReady.wait()
                result = recvData
                head = recvPacketType
                recvDataReady.clear()
                if (head != packetTypes.ACK):
                        print("ack failed")
                        return
                result = None
        """if (packetType == "cleanup"):
                if (contactUsrName == ""):
                        sendQuit = {"fromUsername": username, "toUsername": None, "message": None, "key": None, "additional": None}
                        encryptedSendQuit = fKeyServer.encrypt(json.dumps(sendQuit).encode("utf-8"))
                        client.sendall(struct.pack("!BI", packetTypes.QUITTING, len(encryptedSendQuit))+encryptedSendQuit)
                sendQuit = {"fromUsername": username, "toUsername": contactUsrName, "message": None, "key": None, "additional": None}
                encryptedSendQuit = fKeyServer.encrypt(json.dumps(sendQuit).encode("utf-8"))
                client.sendall(struct.pack("!BI", packetTypes.QUITTING, len(encryptedSendQuit))+encryptedSendQuit)"""
def recvPackets():
        global clientSock
        global recvDataReady
        global recvData
        global undecodedRecvData
        global recvPacketsThreadStarted
        global recvPacketType
        global fKeyRecipient
        client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        clientSock = client
        client.connect((HOST, PORT))
        recvPacketsThreadStarted = True
        while True:
                header = recvExact(client, 5)
                packetType, dataLength = struct.unpack("!BI", header)
                data = recvExact(client, dataLength)    
                recvPacketType = packetType             
                if packetType == packetTypes.SERVERFERNETKEY:
                        recvData = data
                else:
                        recvData = data.decode("utf-8")
                undecodedRecvData = data
                if (packetType == packetTypes.REQCLIENTFERNETKEY):
                        fKeyRecipient = fKeyClient
                        recipientPublicKey = serialization.load_pem_public_key(base64.b64decode(json.loads(fKeyServer.decrypt(recvData))["key"]))
                        encryptedClientFKey = encryptPublicKey(recipientPublicKey, genFKeyClient)
                        clientFkeyDict = {"fromUsername": username, "toUsername": contactUsrName, "message": None, 
                                "key": base64.b64encode(encryptedClientFKey).decode("utf-8"), "additional": None}
                        encryptedCFKD = fKeyServer.encrypt(json.dumps(clientFkeyDict).encode("utf-8"))
                        client.sendall(struct.pack("!BI", packetTypes.SENDCLIENTFERNETKEY, len(encryptedCFKD))+encryptedCFKD)
                if (packetType == packetTypes.MESSAGE):
                        #localTxt = fKeyRecipient.decrypt(fKeyServer.decrypt(recvData))["message"]
                        #client.sendall("fromUsername": username, "toUsername": contactUsrName, "message": None, "key": None, "additional": None)
                        try:
                                window.incomingMessage.emit(data)
                        except NameError:
                                localTxt = None
                                pass
                recvDataReady.set()
                if not data:
                        break
class choose_contact_text(QDialog):
        def __init__(self):
                super().__init__()
                self.setWindowTitle("Choose Contact To Text")
                btns = QDialogButtonBox.Apply | QDialogButtonBox.Close
                self.btnWidget = QDialogButtonBox(btns)
                self.inp = QComboBox()
                self.inp.addItems(contacts)
                btnLayout = QVBoxLayout()
                btnLayout.addWidget(self.inp)
                btnLayout.addWidget(self.btnWidget)
                self.setLayout(btnLayout)
                self.contact_c = ""
                self.usernameForContact = ""
                self.comboAcceptedRan = False
                def comboAccepted(index): #contact_c means contact_chosen
                        self.contact_c = self.inp.itemText(index)
                        self.usernameForContact = contactUsernames[index]
                        self.comboAcceptedRan = True
                        return self.inp.itemText(index)
                self.inp.activated.connect(comboAccepted)
                def accepted():
                        if self.comboAcceptedRan != True:
                                self.contact_c = contacts[0]
                                self.usernameForContact = contactUsernames[0]
                        self.comboAcceptedRan = False
                        self.accept()
                def denied():
                        self.comboAcceptedRan = False
                        self.reject()
                self.btnWidget.button(QDialogButtonBox.Apply).clicked.connect(accepted)
                self.btnWidget.button(QDialogButtonBox.Close).clicked.connect(denied)
class addContact(QDialog):
        def __init__(self):
                super().__init__()
                self.setWindowTitle("Add Contact")

                btns = QDialogButtonBox.Apply | QDialogButtonBox.Close
                self.btnWidget = QDialogButtonBox(btns)

                self.contactInp = QLineEdit()
                self.userInp = QLineEdit()

                self.contactLabel = QLabel("Contact Field: ")
                self.userLabel = QLabel("Username Field: ")

                self.btnLayout = QVBoxLayout()
                self.btnLayout.addWidget(self.contactLabel)
                self.btnLayout.addWidget(self.contactInp)
                self.btnLayout.addWidget(self.userLabel)
                self.btnLayout.addWidget(self.userInp)
                self.btnLayout.addWidget(self.btnWidget)
                self.setLayout(self.btnLayout)
                def accepted():
                        def redoDlgFunc(winTitle: str, text: str):
                                redoDlg = QMessageBox(self)
                                redoDlg.setWindowTitle(winTitle)
                                redoDlg.setText(text)
                                redoDlg.setStandardButtons(QMessageBox.Retry)
                                redoDlg.setIcon(QMessageBox.Warning)
                                redoDlg.exec()
                        if not self.contactInp.text().strip() or not self.userInp.text().strip():
                                redoDlgFunc(winTitle="Redo Inputs", text="One or more text inputs were left empty. Please fill out both of these inputs with a valid username and contact.")
                                return
                        rslt = checkUsername(self.userInp.text(), addC=True)
                        if rslt == True:
                                newContact = {
                                        "contact_name": self.contactInp.text(),
                                        "username": self.userInp.text(),
                                        "status": "",
                                        "msg_cache": ""
                                }
                                dicContacts["contacts"].append(newContact)
                                updateContacts()
                                iterateThroughContacts()
                                self.accept()
                        else:
                                redoDlgFunc(winTitle="Username Doesnt Exist", text="The username you typed doesn't exist in our database. Please check your spelling.")
                                return
                def denied():
                        self.reject()
                self.btnWidget.button(QDialogButtonBox.Apply).clicked.connect(accepted)
                self.btnWidget.button(QDialogButtonBox.Close).clicked.connect(denied)
class mainWin(QMainWindow):
        incomingMessage = pyqtSignal(bytes)
        def __init__(self):
                super().__init__()

                thread = threading.Thread(
                        target=recvPackets,
                        daemon=True
                )
                thread.start()
                def sendMessageWorkflow(msg):
                        global textedBefore
                        if not textedBefore:
                                sendPackets(None, "messagingSetup", msg=msg)
                        if fKeyRecipient is None:
                                print("f ts")
                                return
                        sendPackets(None, "message", msg=msg)
                
                while not recvPacketsThreadStarted:
                        continue
                def addUser_ATriggered():
                        usrInterfaceDlg = addUser()
                        if usrInterfaceDlg.exec():
                                print("add username success")
                        else:
                                print("add username failure")
                def execCCT(): #choose_contact_text
                        global contactMsgName, contactUsrName
                        dlg = choose_contact_text()
                        if dlg.exec():
                                print("sucess")
                        else:
                             	print("failure")
                        contactMsgName = dlg.contact_c
                        contactUsrName = dlg.usernameForContact
                        self.setWindowTitle(f"chat with {contactMsgName}")

                if username != "anonymous":
                        execCCT()
                else:
                        addUser_ATriggered()
                        execCCT()

                if (contactUsrName != noteToSelfUser):
                        threadSendPackets(None, "statusOnlineSend")
                mainWidget = QWidget()
                self.setCentralWidget(mainWidget)

                #toolbar stuff

                toolbar = QToolBar("toolbar")
                self.addToolBar(toolbar) 

                def addContact_ATriggered():
                        dlg1 = addContact()
                        if dlg1.exec():
                                print("add contact success")
                        else:
                                print("add contact failure")
                plusIcon = os.path.join(iconDir, "plus.png")
                addContact_A = QAction(QIcon(plusIcon), "Add Contact", self) #A for action
                addContact_A.triggered.connect(addContact_ATriggered)

                darkPersonIcon = os.path.join(iconDir, "dark_person.png")
                addUserName_A = QAction(QIcon(darkPersonIcon), "Add Your Username", self)
                addUserName_A.triggered.connect(addUser_ATriggered)

                menu = self.menuBar()
                contactMenu = menu.addMenu("&File")
                contactMenu.addAction(addContact_A)
                contactMenu.addSeparator()
                contactMenu.addAction(addUserName_A)

                mainLayout = QVBoxLayout()


                #messages

                msgsLayout = QVBoxLayout()
                self.msgsScroll = QScrollArea()
                self.msgsLayoutContainer = QWidget()
                self.msgsLayoutContainer.setLayout(msgsLayout)

                #local client side texting layout

                sendTxtLayout = QHBoxLayout()
                self.txtInput = QLineEdit()
                self.txtInput.setStyleSheet("border: 1px solid rgba(100, 100, 100, 0.3); border-radius: 10px; background-color: rgba(150, 150, 150, 0.3); font-family: Courier New, Arial;")
                sendTxtLayout.addWidget(self.txtInput)

                #scroll bar properties
                self.msgsScroll.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOn)
                self.msgsScroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
                self.msgsScroll.setWidgetResizable(True)
                def scrollDown():
                        maxOfScroll = self.msgsScroll.verticalScrollBar().maximum()
                        self.msgsScroll.verticalScrollBar().setValue(maxOfScroll)
                self.msgsScroll.setWidget(self.msgsLayoutContainer)

                mainLayout.addWidget(self.msgsScroll)
                mainLayout.addLayout(sendTxtLayout)

                mainWidget.setLayout(mainLayout)
                def setupMsgs(data):
                        try:
                                msgDict = json.loads(fKeyServer.decrypt(data))
                                self.msgs = QLabel(fKeyRecipient.decrypt(base64.b64decode(msgDict["message"])).decode("utf-8"))
                        except Exception as err:
                                print(err)
                                msgDict = json.loads(data)
                                self.msgs = QLabel(msgDict["message"])
                        self.msgs.setWordWrap(True)
                        self.msgs.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Minimum)
                        self.msgs.setStyleSheet("""border: 1px solid rgba(90, 90, 90, 1);
                                                border-radius: 10px;
                                                color: rgb(255, 255, 255);
                                                background-color: rgba(90, 90, 90, 1);
                                                font-family: Courier New, Arial;
                                                padding: 5px;
                                                """)
                        msgsLayout.addWidget(self.msgs, alignment=Qt.AlignLeft)
                self.localTxt = None
                def sendTxt():
                        #msgs_s for msgs send - what the client sends to the server
                        self.msgs_s = QLabel(self.txtInput.text())
                        self.msgs_s.setWordWrap(True)
                        self.msgs_s.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Minimum)
                        self.msgs_s.setStyleSheet("""border: 1px solid rgba(70, 70, 255, 1);
                                                  border-radius: 10px; color: rgb(255, 255, 255);
                                                  background-color: rgba(70, 70, 255, 1);
                                                  font-family: Courier New, Arial;
                                                  padding: 5px;
                                                  """)
                        msgsLayout.addWidget(self.msgs_s, alignment=Qt.AlignRight)
                        try:
                                if contactUsrName == noteToSelfUser:
                                        val = {"fromUsername": username, "toUsername": username, "message": self.txtInput.text()}
                                        val = json.dumps(val)
                                        self.txtInput.clear()
                                        setupMsgs(val)
                                        return
                                val = self.txtInput.text()
                                threading.Thread(
                                target=sendMessageWorkflow,
                                        args=(str(val),),
                                        daemon=True
                                ).start()
                        except Exception as e:
                                QMessageBox.critical(self, "Error", f"failed to process: {e}")
                        else:
                                self.txtInput.clear()
                self.txtInput.returnPressed.connect(sendTxt)
                self.incomingMessage.connect(setupMsgs)
                self.msgsScroll.verticalScrollBar().rangeChanged.connect(scrollDown)
#def cleanup():
        #closedYet = False

app = QApplication(sys.argv)
window = mainWin()
window.show()
#app.aboutToQuit.connect()
app.exec()
