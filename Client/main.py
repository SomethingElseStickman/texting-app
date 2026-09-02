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
from cryptography.hazmat.primitives.asymmetric import rsa, padding
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.fernet import Fernet
HOST =  "127.0.0.1"
PORT = 65432
noteToSelfUser = "127.0.0.1"

genFKey = Fernet.generate_key() #fernet key generated for symmetrical encryption
fKey = Fernet(genFKey) #store the generated fernet key
genServerFKey = Fernet.generate_key()
serverFKey = Fernet(genServerFKey)
privateKey = rsa.generate_private_key(public_exponent=65537, key_size=2048)
publicKey = privateKey.public_key()
serverPublicKey = None
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
def convertPKToBytes(key):
        publicKeyBytes = key.public_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PublicFormat.SubjectPublicKeyInfo
        return publicKeyBytes
)
clientSock = None
recvData = False
recvDataReady = threading.Event()
incomingMsg = threading.Event()
recvPacketsThreadStarted = False
fileDir = os.path.dirname(__file__)
iconDir = os.path.join(fileDir, "icons")
with open("contacts.json", "r", encoding="utf-8") as f:
        jsonContacts = f.read()
dicContacts = json.loads(jsonContacts)
print(dicContacts)
username = dicContacts["username"]
contacts = []
contactUsernames = []
contactStatuses = []
contactMsgName = ""
contactUsrName = ""
temp = None
interv = 0
localTxt = None
startUp = False
onlineNotifier = 1 #tells send packets func if we are just notifying online status or are sending a text message
#iterates through the contact json script
def threadSendPackets(usernameAuth: string, msg="disregard this message - sent by program DISREGARD"):
        th = threading.Thread(
                target=sendPackets,
                args=(usernameAuth, msg),
                daemon=True
        )
        th.start()
def iterateThroughContacts():
        global contacts, contactUsernames, contactStatuses
        for contact in dicContacts["contacts"]:
                contacts.append(contact["contact_name"])
                contactUsernames.append(contact["username"])
                contactStatuses.append(contact["status"])
iterateThroughContacts()
def updateContacts():
        with open("contacts.json", "w", encoding="utf-8") as f:
                f.write(json.dumps(dicContacts, indent=4))
#send packets to the server
#NOTE: right now it just sends the text back to the sender
def checkUsername(tmp: string, addC=False): #tmp for the userauth but im too lazy to make a name for that also addC for addcontact var
        global onlineNotifier
        onlineNotifier = 2
        print(tmp)
        if tmp != noteToSelfUser:
                threadSendPackets(usernameAuth=tmp)
        else:
                return True
        def mainL(): #main logic
                global onlineNotifier
                print(onlineNotifier)
                onlineNotifier = 0
        if onlineNotifier == 735:
                if addC == False: #return for if func is checking if user is in database
                        mainL()
                        return True
                else: #return for if func is checking if the user is not in the database
                        mainL()
                        return False
        elif onlineNotifier == 4063:
                if addC == False:
                        mainL()
                        return False
                else:
                        mainL()
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
def sendPackets(usernameAuth: string, msg="disregard this message - sent by program DISREGARD", mode: string):
        global onlineNotifier
        global localTxt
        global recvData
        global serverPublicKey
        client = clientSock
        pem = None
        if recvDataReady and not startUp:
                startUp = True
                pem = recvData
                serverPublicKey = load_pem_public_key(pem)
                SFKTEMPpublicKey = encryptPublicKey(serverPublicKey, serverFKey)#server fernet key temporary (for the symmetrical encryption with server)
                pemSFK = convertPKToBytes(SFKTEMPpublicKey)
                client.sendall(pemSFK + b"\n")
        if mode == "checkUsr":

        elif mode == "checkUsrExists":
                pass
        elif mode == "text":
                pass

def recvPackets():
        global clientSock
        global recvDataReady
        global recvData
        global recvPacketsThreadStarted
        client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        clientSock = client
        client.connect((HOST, PORT))
        recvPacketsThreadStarted = True
        def recvProtocol(byteString):
                while byteString.find("\n") == -1:
                time.sleep(0.1)
        while True:
                data = client.recv(1024)
                if data:
                        recvProtocol()
                        recvData = data.decode()
                        recvDataReady.set()
                        try:
                                window.incomingMessage.emit(recvData)
                        except NameError:
                                pass
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
                        def redoDlgFunc(winTitle: string, text: string):
                                redoDlg = QMessageBox(self)
                                redoDlg.setWindowTitle(winTitle)
                                redoDlg.setText(text)
                                redoDlg.setStandardButtons(QMessageBox.Retry)
                                redoDlg.setIcon(QMessageBox.Warning)
                                redoDlg.exec()
                        if (self.contactInp or self.userInp) == "":
                                redoDlgFunc(winTitle="Redo Inputs", text="One or more text inputs were left empty. Please fill out both of these inputs with a valid username and contact.")
                                return
                        rslt = checkUsername(self.userInp.text(), True)
                        if rslt == True:
                                newContact = {
                                        "contact_name" : self.contactInp.text(),
                                        "username" : self.userInp.text(),
                                        "status" : ""
                                }
                                dicContacts["contacts"].append(newContact)
                                updateContacts()
                                iterateThroughContacts()
                                print("new contact added")
                                self.accept()
                        else:
                                redoDlgFunc(winTitle="Username Doesnt Exist", text="The username you typed doesn't exist in our database. Please check your spelling.")
                                return
                def denied():
                        self.reject()
                self.btnWidget.button(QDialogButtonBox.Apply).clicked.connect(accepted)
                self.btnWidget.button(QDialogButtonBox.Close).clicked.connect(denied)
class mainWin(QMainWindow):
        incomingMessage = pyqtSignal(str)
        def __init__(self):
                super().__init__()

                thread = threading.Thread(
                        target=recvPackets,
                        daemon=True
                )
                thread.start()
                while not recvPacketsThreadStarted:
                        continue
                if (contactUsrName != noteToSelfUser):
                        threadSendPackets(None)
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
                        msgDict = json.loads(fKey.decrypt(data))
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
                                        val = '{"fromUsername": username, "toUsername": username, "message": self.txtInput.text()}'
                                        val = json.loads(val)
                                        self.txtInput.clear()
                                        setupMsgs(val)
                                        return
                                val = self.txtInput.text()
                                threadSendPackets(usernameAuth=None, msg=str(val))
                        except Exception as e:
                                QMessageBox.critical(self, "Error", f"failed to process: {e}")
                        else:
                                self.txtInput.clear()
                self.txtInput.returnPressed.connect(sendTxt)
                self.incomingMessage.connect(setupMsgs)

                self.msgsScroll.verticalScrollBar().rangeChanged.connect(scrollDown)
app = QApplication(sys.argv)
window = mainWin()
window.show()
app.exec()
