#libraries for communicating with web server
import socket
import time
import sys

#libraries for local net UI
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
                            QLabel, QPushButton, QSlider, QLineEdit, QComboBox, 
                            QGroupBox, QGridLayout, QTabWidget, QMessageBox, QSpinBox,
                            QProgressDialog, QDialog, QListWidget, QCheckBox, QDateTimeEdit, QDateEdit, QDial,
                            QDoubleSpinBox, QFontComboBox, QLCDNumber, QProgressBar, QRadioButton, QTimeEdit,
                            QSizePolicy)

#libraries for multithreading
from PyQt5.QtCore import Qt, QTimer, pyqtSignal, pyqtSlot, QThread, QSize
import os
import sys

class mainWindow(QMainWindow):
	def __init__(self):
			super().__init__()
			
			self.setWindowTitle("LaserBot Controls")
			layout = QVBoxLayout()

			#need to replace this with adding it individually
			"""
			widgets = [
			
			QCheckBox,
			QComboBox,
			QDateTimeEdit,
			QDial,
			QDoubleSpinBox,
			QLCDNumber,
			QLabel,
			QLineEdit,
			QProgressBar,
			QPushButton,
			QRadioButton,
			QSlider,
			QSpinBox,
			QTimeEdit
			
			
			]
			
			for w in widgets:
				layout.addWidget(w())
			"""
			
			#Start/Stop Section
			
				#Start/Stop Label
			startStopText = QLabel("Startup Protocols")
			font = startStopText.font()
			startStopText.setFont(font)
			startStopText.setAlignment(Qt.AlignTop)
			layout.addWidget(startStopText)
			
				#Horizontal Layout for Start/Stop Section
			horizontalLayout = QHBoxLayout()
			horizontalLayout.setAlignment(Qt.AlignTop)
			layout.addLayout(horizontalLayout)
				
					#On Button: Start/Stop Section
			startButton = QPushButton("On")
			horizontalLayout.addWidget(startButton)
			
					#Off Button: Start/Stop Section
			stopButton = QPushButton("Off")
			horizontalLayout.addWidget(stopButton)
			
					#Diagnostic Button: Start/Stop Section
			diagnosticButton = QPushButton("Diagnostic")
			horizontalLayout.addWidget(diagnosticButton)
					
					#Link section together
			layout.addStretch()
			
			#Autonomous Section
				
				#Horizontal Layout for Autonomous Protocols
			horizontalLayout = QHBoxLayout()
			horizontalLayout.setAlignment(Qt.AlignTop)
			layout.addLayout(horizontalLayout)
			
					#Autonomous Protocols Label
			autonomousProtocolText = QLabel("Autonomous Protocols")
			font = autonomousProtocolText.font()
			autonomousProtocolText.setFont(font)
			autonomousProtocolText.setAlignment(Qt.AlignTop)
			horizontalLayout.addWidget(autonomousProtocolText)
			
					#Progress Bar
			autonomousProgressBar = QProgressBar()
			autonomousProgressBar.setGeometry(200, 150, 200, 30)
			autonomousProgressBar.setRange(0, 100)
			autonomousProgressBar.setValue(0)
			completion = autonomousProgressBar.value()
			horizontalLayout.addWidget(autonomousProgressBar)
		
				#Horizontal Layoutout for AP Combobox and Send
			horizontalLayout = QHBoxLayout()
			horizontalLayout.setAlignment(Qt.AlignTop)
			layout.addLayout(horizontalLayout)
			
					#Protocols Combobox
			autonomousComboBox = QComboBox()
			autonomousProtocolsList = ["","Home", "Move X Axis"]
			autonomousComboBox.addItems(autonomousProtocolsList)
			policy = autonomousComboBox.sizePolicy()
			policy.setHorizontalPolicy(QSizePolicy.Expanding)
			autonomousComboBox.setSizePolicy(policy)
			horizontalLayout.addWidget(autonomousComboBox)
					
					#Send Button: Autonomous Protocols
			as_sendButton = QPushButton("Send")
						#When protocol is sent, moveProgressBar is called
			as_sendButton.clicked.connect(lambda: self.moveProgressBar(autonomousProgressBar, autonomousComboBox.currentText(), consoleText))
			horizontalLayout.addWidget(as_sendButton)
			
				#Link Section together
			layout.addStretch()
				
			#Console Section
			consoleLabel = QLabel("Output Console")
			font = consoleLabel.font()
			consoleLabel.setFont(font)
			consoleLabel.setAlignment(Qt.AlignTop)
			layout.addWidget(consoleLabel)
			
			consoleText = QLabel("")
			consoleText.setStyleSheet("background-color: white;")
			font = consoleText.font()
			consoleText.setFont(font)
			consoleText.setAlignment(Qt.AlignTop)
			layout.addWidget(consoleText)
			
			layout.addStretch()
			
			#Window Section
			
			widget = QWidget()
			widget.setLayout(layout)
			#self.setMinimumSize(QSize(450, 450))
			self.setCentralWidget(widget)
			
			
			
	def executeProtocol(self, comboBoxText, consoleText):
		#insert logic here to execute protocol based off of comboBoxText
		print("Executing Protocol: " + comboBoxText)
		consoleText.setText("Executing Protocol: " + comboBoxText)		
		
	def moveProgressBar(self, autonomousProgressBar, comboBoxText, consoleText):
		#modify logic here to get a time of it running. how to get live time?
		self.executeProtocol(comboBoxText, consoleText)
		completion = 0
		while completion <100:
			time.sleep(0.1)
			completion += 1
			autonomousProgressBar.setValue(completion)
	



			
def initialize_ui():
	app = QApplication(sys.argv)
	window = mainWindow()
	window.show()
	app.exec()

def initialize_control_words():
	# Digitale Eingänge 60FDh
	# digital inputs
	DInputs = [0, 0, 0, 0, 0, 13, 0, 43, 13, 0, 0, 0, 96, 253, 0, 0, 0, 0, 4]  
	DInputs_array = bytearray(DInputs)
	print(DInputs_array)


	# Statusword 6041h
	# Status request
	# has 19 values
	#         0  1  2  3  4  5   6  7   8   9  10 11  12  13 14 15 16 17 18
	status = [0, 0, 0, 0, 0, 13, 0, 43, 13, 0,  0, 0, 96, 65, 0, 0, 0, 0, 2]
	status_array = bytearray(status)
	print(status_array)

	# Controlword 6040h
	# Command: Shutdown
	#has 21 values
	#BYTE 18: signifies how many bits we're sending
	#BYTE 19-22: DATA READS AND WRITES 
	#			0  1  2  3  4   5  6   7   8  9  10 11  12  13 14 15 16 17 18 19 20
	shutdown = [0, 0, 0, 0, 0, 15, 0, 43, 13, 1,  0, 0, 96, 64, 0, 0, 0, 0, 2, 6, 0]
	shutdown_array = bytearray(shutdown)
	print(shutdown_array)

	# Controlword 6040h
	# Command: Switch on
	switchOn = [0, 0, 0, 0, 0, 15, 0, 43, 13, 1, 0, 0, 96, 64, 0, 0, 0, 0, 2, 7, 0]
	switchOn_array = bytearray(switchOn)
	print(switchOn_array)

	# Controlword 6040h
	# Command: enable Operation
	enableOperation = [0, 0, 0, 0, 0, 15, 0, 43,13, 1, 0, 0, 96, 64, 0, 0, 0, 0, 2, 15, 0]
	enableOperation_array = bytearray(enableOperation)
	print(enableOperation_array)

	# Controlword 6040h
	# Command: stop motion
	stop = [0, 0, 0, 0, 0, 15, 0, 43,13, 1, 0, 0, 96, 64, 0, 0, 0, 0, 2, 15, 1]
	stop_array = bytearray(stop)
	print(stop_array)

	# Controlword 6040h
	# Command: reset dryve
	reset = [0, 0, 0, 0, 0, 15, 0, 43,13, 1, 0, 0, 96, 64, 0, 0, 0, 0, 2, 0, 1]
	reset_array = bytearray(reset)
	print(reset_array)

	# Variables start value
	start = 0
	ref_done = 0
	error = 0
	
	
def initialize_socket_and_communications():
	print("Initializing socket.")
	#Establish bus connection
	try:
		s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
	except socket.error:
		print ('failed to create sockt')
		
	s.connect(("169.254.239.1", 502))
	print ('Socket created')
	#When executing the program and the shell displays the storing folder and the program name, the set IP address in the program and the dryve D1 doesn't match
	
#Definition of the function to send and receive data 
def sendCommand(data):
    #Create socket and send request
    s.send(data)
    res = s.recv(24)
    #Print response telegram
    print(list(res))
    return list(res)
    
#sending Shutdown Controlword and check the following Statusword. Checking several Statuswords because of various options. look at Bit assignment Statusword, data package in user manual 
def set_shdn():
    sendCommand(reset_array)
    sendCommand(shutdown_array)
    while (sendCommand(status_array) != [0, 0, 0, 0, 0, 15, 0, 43, 13, 0, 0, 0, 96, 65, 0, 0, 0, 0, 2, 33, 6]
           and sendCommand(status_array) != [0, 0, 0, 0, 0, 15, 0, 43, 13, 0, 0, 0, 96, 65, 0, 0, 0, 0, 2, 33, 22]
           and sendCommand(status_array) != [0, 0, 0, 0, 0, 15, 0, 43, 13, 0, 0, 0, 96, 65, 0, 0, 0, 0, 2, 33, 2]):
        print("wait for shdn")

        #1 second delay
        time.sleep(1)
        
#sending Switch on Disabled Controlword and check the following Statusword. Checking several Statuswords because of various options. look at Bit assignment Statusword, data package in user manual 
def set_swon():
    sendCommand(switchOn_array)
    while (sendCommand(status_array) != [0, 0, 0, 0, 0, 15, 0, 43, 13, 0, 0, 0, 96, 65, 0, 0, 0, 0, 2, 35, 6]
           and sendCommand(status_array) != [0, 0, 0, 0, 0, 15, 0, 43, 13, 0, 0, 0, 96, 65, 0, 0, 0, 0, 2, 35, 22]
           and sendCommand(status_array) != [0, 0, 0, 0, 0, 15, 0, 43, 13, 0, 0, 0, 96, 65, 0, 0, 0, 0, 2, 35, 2]):
        print("wait for sw on")

        time.sleep(1)
        
#Operation Enable Controlword and check the following Statusword. Checking several Statuswords because of various options. look at Bit assignment Statusword, data package in user manual 
def set_op_en():
    sendCommand(enableOperation_array)
    while (sendCommand(status_array) != [0, 0, 0, 0, 0, 15, 0, 43, 13, 0, 0, 0, 96, 65, 0, 0, 0, 0, 2, 39, 6]
           and sendCommand(status_array) != [0, 0, 0, 0, 0, 15, 0, 43, 13, 0, 0, 0, 96, 65, 0, 0, 0, 0, 2, 39, 22]
           and sendCommand(status_array) != [0, 0, 0, 0, 0, 15, 0, 43, 13, 0, 0, 0, 96, 65, 0, 0, 0, 0, 2, 39, 2]):
        print("wait for op en")

        time.sleep(1)


def init_set():

    #Call of the function sendCommand to start the State Machine with the previously defined telegrams (Manual: Visualisation State Machine)
    set_mode(1)
    sendCommand(reset_array)
    set_shdn()
    set_swon()
    set_op_en()

def set_mode(mode):

    #Set operation modes in object 6060h Modes of Operation
    c
    while (sendCommand(bytearray([0, 0, 0, 0, 0, 13, 0, 43, 13, 0, 0, 0, 96, 97, 0, 0, 0, 0, 1])) != [0, 0, 0, 0, 0, 14, 0, 43, 13, 0, 0, 0, 96, 97, 0, 0, 0, 0, 1, mode]):

        print("wait for mode")

        time.sleep(0.1)
        
def homing ():
    #Reset the start bit in Controlword
    sendCommand(enableOperation_array)
    
    #Parameterization of the objects according to the manual
    #6060h Modes of Operation
    #Set Homing mode (see "def set_mode(mode):"; Byte 19 = 6)
    set_mode(6)
    
    # 6092h_01h Feed constant Subindex 1 (Feed)
    #Set feed constant to 5400 (axis in Video); refer to manual (Byte 19 = 24; Byte 20 = 21; Byte 21 = 0; Byte 22 = 0)
    sendCommand(bytearray([0, 0, 0, 0, 0, 17, 0, 43, 13, 1, 0, 0, 96, 146, 1, 0, 0, 0, 4, 24, 21, 0, 0]))
    
    # 6092h_02h Feed constant Subindex 2 (Shaft revolutions)
    #Set shaft revolutions to 1; refer to manual (Byte 19 = 1; Byte 20 = 0; Byte 21 = 0; Byte 22 = 0)
    sendCommand(bytearray([0, 0, 0, 0, 0, 17, 0, 43, 13, 1, 0, 0, 96, 146, 2, 0, 0, 0, 4, 1, 0, 0, 0]))
    
    # 6099h_01h Homing speeds Switch
    #Speed during search for switch is set to 60 rpm (Byte 19 = 112; Byte 20 = 23; Byte 21 = 0; Byte 22 = 0)
    sendCommand(bytearray([0, 0, 0, 0, 0, 17, 0, 43, 13, 1, 0, 0, 96, 153, 1, 0, 0, 0, 4, 112, 23, 0, 0]))
    
    # 6099h_02h Homing speeds Zero
    #Set speed during Search for zero to 60 rpm (Byte 19 = 112; Byte 20 = 23; Byte 21 = 0; Byte 22 = 0)
    sendCommand(bytearray([0, 0, 0, 0, 0, 17, 0, 43, 13, 1, 0, 0, 96, 153, 2, 0, 0, 0, 4, 112, 23, 0, 0]))
    
    # 609Ah Homing acceleration
    #Set Homing acceleration to 1000 rpm/min² (Byte 19 = 160; Byte 20 = 134; Byte 21 = 1; Byte 22 = 0)
    sendCommand(bytearray([0, 0, 0, 0, 0, 17, 0, 43, 13, 1, 0, 0, 96, 154, 0, 0, 0, 0, 4, 160, 134, 1, 0]))
    
    # 6040h Controlword
    #Start Homing
    sendCommand(bytearray([0, 0, 0, 0, 0, 15, 0, 43, 13, 1, 0, 0, 96, 64, 0, 0, 0, 0, 2, 31, 0]))
    
    #Check Statusword for signal referenced and if an error in the D1 comes up
    while (sendCommand(status_array) != [0, 0, 0, 0, 0, 15, 0, 43, 13, 0, 0, 0, 96, 65, 0, 0, 0, 0, 2, 39, 22]
        and sendCommand(status_array) != [0, 0, 0, 0, 0, 15, 0, 43, 13, 0, 0, 0, 96, 65, 0, 0, 0, 0, 2, 8, 6]
        and sendCommand(status_array) != [0, 0, 0, 0, 0, 15, 0, 43, 13, 0, 0, 0, 96, 65, 0, 0, 0, 0, 2, 8, 34]
        and sendCommand(status_array) != [0, 0, 0, 0, 0, 15, 0, 43, 13, 0, 0, 0, 96, 65, 0, 0, 0, 0, 2, 8, 2]):
            #If the StopButton is pushed the loop breaks
            if sendCommand(DInputs_array) == [0, 0, 0, 0, 0, 17, 0, 43, 13, 0, 0, 0, 96, 253, 0, 0, 0, 0, 4, 8, 0, 66, 0]:
                break
            time.sleep(0.1)
            print ("Homing")
            
#1:06 PM 8/12/25
# broke down aux functions, except movement and main. wtf is the beginning movement in main

#might have to change name to moveProtocol, might make more sense
def main_programm():
	#Ask if there is an Error on D1            
	if (sendCommand(status_array) == [0, 0, 0, 0, 0, 15, 0, 43, 13, 0, 0, 0, 96, 65, 0, 0, 0, 0, 2, 8, 22]
		or sendCommand(status_array) == [0, 0, 0, 0, 0, 15, 0, 43, 13, 0, 0, 0, 96, 65, 0, 0, 0, 0, 2, 8, 6]
		or sendCommand(status_array) == [0, 0, 0, 0, 0, 15, 0, 43, 13, 0, 0, 0, 96, 65, 0, 0, 0, 0, 2, 8, 34]
		or sendCommand(status_array) == [0, 0, 0, 0, 0, 15, 0, 43, 13, 0, 0, 0, 96, 65, 0, 0, 0, 0, 2, 8, 2] ):
			error = 1
	else: 
		error = 0
		
	#If no Error is up start the initialisierung    
	if error == 0:
		init()
		time.sleep(0.5)
		#If there is no error, the system waits for a start command
		while error == 0:        
			if sendCommand(DInputs_array) == [0, 0, 0, 0, 0, 17, 0, 43, 13, 0, 0, 0, 96, 253, 0, 0, 0, 0, 4, 8, 0, 65, 0]:
				start = 1
				
			time.sleep(0.1)
			#When Start is pressed start of the homing
			while start == 1:
				homing()
				#Query whether someone has stopped during the homings or an error has occurred
				if (sendCommand(DInputs_array) == [0, 0, 0, 0, 0, 17, 0, 43, 13, 0, 0, 0, 96, 253, 0, 0, 0, 0, 4, 8, 0, 66, 0]
					or sendCommand(status_array) == [0, 0, 0, 0, 0, 15, 0, 43, 13, 0, 0, 0, 96, 65, 0, 0, 0, 0, 2, 8, 6]
					or sendCommand(status_array) == [0, 0, 0, 0, 0, 15, 0, 43, 13, 0, 0, 0, 96, 65, 0, 0, 0, 0, 2, 8, 34]
					or sendCommand(status_array) == [0, 0, 0, 0, 0, 15, 0, 43, 13, 0, 0, 0, 96, 65, 0, 0, 0, 0, 2, 8, 2] ):
						break
						
				ref_done = 1
				#6060h Modes of Operation
				#Set Profile Position Mode (see "def set_mode(mode):"; Byte 19 = 1)
				set_mode(1)
				#For as long as referenced, the normal movement is started.
				while ref_done == 1:
					#Call Movement A
					#movement_A()
					#If Movement A is stopped while driving or an error has occurred, the loop is interrupted
					#if (sendCommand(DInputs_array) == [0, 0, 0, 0, 0, 17, 0, 43, 13, 0, 0, 0, 96, 253, 0, 0, 0, 0, 4, 8, 0, 66, 0]
						#or sendCommand(status_array) == [0, 0, 0, 0, 0, 15, 0, 43, 13, 0, 0, 0, 96, 65, 0, 0, 0, 0, 2, 8, 6]):
							#break
					#time.sleep(0.5)
					#Call Movement B
					movement_B()
					#If Movement B is stopped while driving or an error has occurred, the loop is interrupted
					if (sendCommand(DInputs_array) == [0, 0, 0, 0, 0, 17, 0, 43, 13, 0, 0, 0, 96, 253, 0, 0, 0, 0, 4, 8, 0, 66, 0]
						or sendCommand(status_array) == [0, 0, 0, 0, 0, 15, 0, 43, 13, 0, 0, 0, 96, 65, 0, 0, 0, 0, 2, 8, 6]):
							break
					time.sleep(0.5)    
				#If Motionbstopped while driving or an error has occurred, the loop is interrupted
				if (sendCommand(DInputs_array) == [0, 0, 0, 0, 0, 17, 0, 43, 13, 0, 0, 0, 96, 253, 0, 0, 0, 0, 4, 8, 0, 66, 0]
					or sendCommand(status_array) == [0, 0, 0, 0, 0, 15, 0, 43, 13, 0, 0, 0, 96, 65, 0, 0, 0, 0, 2, 8, 22]
					or sendCommand(status_array) == [0, 0, 0, 0, 0, 15, 0, 43, 13, 0, 0, 0, 96, 65, 0, 0, 0, 0, 2, 8, 6]):
						break
				  
			#If stopped, the movement is stopped         
			if sendCommand(DInputs_array) == [0, 0, 0, 0, 0, 17, 0, 43, 13, 0, 0, 0, 96, 253, 0, 0, 0, 0, 4, 8, 0, 66, 0]:
				start = 0
				sendCommand(stop_array)
			#If an error has occurred, the loop is interrupted    
			if (sendCommand(status_array) == [0, 0, 0, 0, 0, 15, 0, 43, 13, 0, 0, 0, 96, 65, 0, 0, 0, 0, 2, 8, 22]
					or sendCommand(status_array) == [0, 0, 0, 0, 0, 15, 0, 43, 13, 0, 0, 0, 96, 65, 0, 0, 0, 0, 2, 8, 6]
					or sendCommand(status_array) == [0, 0, 0, 0, 0, 15, 0, 43, 13, 0, 0, 0, 96, 65, 0, 0, 0, 0, 2, 8, 34]
					or sendCommand(status_array) == [0, 0, 0, 0, 0, 15, 0, 43, 13, 0, 0, 0, 96, 65, 0, 0, 0, 0, 2, 8, 2]):
					error = 1
					break
			print ("Wait for Start")
	   
	print("Error on D1")

if __name__ == '__main__':
	appStartUp = initialize_ui()
	initialize_socket_and_communications()
	initialize_control_words()
	main_programm()
	
	

