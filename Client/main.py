import socket
from PyQt5.QtWidgets import (
QApplication, QMainWindow, QLineEdit, QMessageBox, QVBoxLayout, QLabel, 
QHBoxLayout, QScrollArea, QWidget, QDialog, QDialogButtonBox, QComboBox, 
QToolBar, QAction
)
#TODO add username selection and allow server to send back information about contacts.
#TODO add labels for adding contact input fields for clarity
#TODO send to server a handshake that sees if the username selected for contact adding is in the database.
from PyQt5.QtGui import QIcon
from PyQt5.QtCore import QSize, Qt
import threading
import sys
import json
import hashlib
import os
HOST =  "127.0.0.1"
PORT = 65432
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
temp = None
interv = 0
onlineNotifier = 1 #tells send packets func if we are just notifying online status or are sending a text message
#iterates through the contact json script
def iterateThroughContacts():
        global contacts, contactUsernames, contactStatuses
        for contact in dicContacts["contacts"]:
                contacts.append(contact["contact_name"])
                contactUsernames.append(contact["username"])
                contactStatuses.append(contact["status"])
iterateThroughContacts()
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
class addContact(QDialog):
        def __init__(self):
                super().__init__()
                self.setWindowTitle("Add Contact")

                btns = QDialogButtonBox.Apply | QDialogButtonBox.Close
                self.btnWidget = QDialogButtonBox(btns)

                self.contactInp = QLineEdit()
                self.userInp = QLineEdit()

                self.btnLayout = QVBoxLayout()
                self.btnLayout.addWidget(self.contactInp)
                self.btnLayout.addWidget(self.userInp)
                self.btnLayout.addWidget(self.btnWidget)
                self.setLayout(self.btnLayout)
                def accepted():
                        if (self.contactInp or self.userInp) == "":
                                redoDlg = QMessageBox(self)
                                redoDlg.setWindowTitle("Redo Inputs")
                                redoDlg.setText("One or more text inputs was left empty. Please fill both these inputs in with a valid username and a contact")
                                redoDlg.setStandardButtons(QMessageBox.Retry)
                                redoDlg.setIcon(QMessageBox.Warning)
                                redoDlg.exec()
                                return
                        newContact = {
                                "contact_name" : self.contactInp.text(),
                                "username" : self.userInp.text(),
                                "status" : ""
                        }
                        dicContacts["contacts"].append(newContact)
                        with open("contacts.json", "w", encoding="utf-8") as f:
                                f.write(json.dumps(dicContacts, indent=4))
                        iterateThroughContacts()
                        print("new contact added")
                        self.accept()
                def denied():
                        self.reject()
                self.btnWidget.button(QDialogButtonBox.Apply).clicked.connect(accepted)
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
                changeDisplayName_A = QAction(QIcon(darkPersonIcon), "Change Display Name", self)

                menu = self.menuBar()
                contactMenu = menu.addMenu("&File")
                contactMenu.addAction(addContact_A)
                contactMenu.addSeparator()
                contactMenu.addAction(changeDisplayName_A)

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
