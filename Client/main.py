import socket
from PyQt5.QtWidgets import (
QApplication, QMainWindow, QLineEdit, QMessageBox, QVBoxLayout, QLabel, 
QHBoxLayout, QScrollArea, QWidget, QDialog, QDialogButtonBox, QComboBox
)
#TODO make chosen_contact_text.inp QComboBox() to allow user to select multiple contacts to text
from PyQt5.QtCore import QSize, Qt
import threading
import sys
import json
import hashlib
HOST =  "127.0.0.1"
PORT = 65432
with open("contacts.json", "r", encoding="utf-8") as f:
        jsonContacts = f.read()
dicContacts = json.loads(jsonContacts)
print(dicContacts)
username = dicContacts["username"]
contacts = []
contactIps = []
contactStatuses = []
temp = None
interv = 0
onlineNotifier = 1 #tells send packets func if we are just notifying online status or are sending a text message
#iterates through the contact json script
for contact in dicContacts["contacts"]:
        contacts.append(contact["contact_name"])
        contactIps.append(contact["ip"])
        contactStatuses.append(contact["status"])
#send packets to the server
#NOTE: right now it just sends the text back to the sender
def sendPackets(msg="disregard this message - sent by program DISREGARD"):
        global onlineNotifier
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as client:
                client.connect((HOST, PORT))
                if onlineNotifier != 1:
                        client.sendall(msg.encode("utf-8"))
                        data = client.recv(1024)
                        return data
                else:
                        client.sendall(str(hashlib.sha256("online".encode("utf-8")).hexdigest()).encode("utf-8"))
                        result = client.recv(1024)
                        if result.decode() == "1":
                                client.sendall(username.encode("utf-8"))
                                onlineNotifier = 0
sendPackets()
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
                self.comboAcceptedRan = False
                def comboAccepted(index): #contact_c means contact_chosen
                        self.contact_c = self.inp.itemText(index)
                        self.comboAcceptedRan = True
                        return self.inp.itemText(index)
                self.inp.activated.connect(comboAccepted)
                def accepted():
                        if self.comboAcceptedRan != True:
                                self.contact_c = contacts[0]
                        self.comboAcceptedRan = False
                        self.accept()
                def denied():
                        self.comboAcceptedRan = False
                        self.reject()
                self.btnWidget.button(QDialogButtonBox.Apply).clicked.connect(accepted)
                self.btnWidget.button(QDialogButtonBox.Close).clicked.connect(denied)
class mainWin(QMainWindow):
        def __init__(self):
                super().__init__()
                dlg = choose_contact_text()
                if dlg.exec():
                        print("sucess")
                else:
                        print("failure")
                contactMsgName = dlg.contact_c
                self.setWindowTitle(f"chat with {contactMsgName}")

                mainWidget = QWidget()
                self.setCentralWidget(mainWidget)

                mainLayout = QVBoxLayout()

                #messages

                msgsLayout = QVBoxLayout()
                self.msgsScroll = QScrollArea()
                self.msgsLayoutContainer = QWidget()
                self.msgsLayoutContainer.setLayout(msgsLayout)

                #local client side texting layout

                sendTxtLayout = QHBoxLayout()
                self.txtInput = QLineEdit()
                sendTxtLayout.addWidget(self.txtInput)

                #scroll bar properties

                self.msgsScroll.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOn)
                self.msgsScroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
                self.msgsScroll.setWidgetResizable(True)
                self.msgsScroll.setWidget(self.msgsLayoutContainer)

                mainLayout.addWidget(self.msgsScroll)
                mainLayout.addLayout(sendTxtLayout)

                mainWidget.setLayout(mainLayout)
                def setupMsgs():
                        self.msgs = QLabel(self.localTxt.decode("utf-8"))
                        msgsLayout.addWidget(self.msgs)
                self.localTxt = ""
                def sendTxt():
                        #msgs_s for msgs send - what the client sends to the server
                        self.msgs_s = QLabel(self.txtInput.text())
                        msgsLayout.addWidget(self.msgs_s, alignment=Qt.AlignRight)
                        try:
                                val = self.txtInput.text()
                                self.localTxt = sendPackets(str(val))
                        except Exception as e:
                                QMessageBox.warning(self, "Error", f"failed to process: {e}")
                        else:
                                setupMsgs()
                                self.txtInput.clear()
                self.txtInput.returnPressed.connect(sendTxt) 
app = QApplication(sys.argv)

window = mainWin()
window.show()
app.exec()
