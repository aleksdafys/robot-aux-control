import sys
import socket
import time
import threading
from PyQt5.QtWidgets import (QApplication, QMainWindow, QPushButton, QVBoxLayout, 
                            QHBoxLayout, QWidget, QLabel, QComboBox, QSpinBox,
                            QGroupBox, QTextEdit, QLineEdit, QGridLayout)
from PyQt5.QtCore import Qt, QTimer, pyqtSignal, QObject

class ModbusTCPGateway(QObject):
    status_update = pyqtSignal(str)
    statusword_update = pyqtSignal(int)
    
    def __init__(self):
        super().__init__()
        self.sock = None
        self.connected = False
        self.transaction_id = 0
        
    def connect(self, ip_address, port=502):
        try:
            self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.sock.settimeout(5)
            self.sock.connect((ip_address, port))
            self.connected = True
            self.status_update.emit(f"Connected to {ip_address}:{port}")
            return True
        except Exception as e:
            self.status_update.emit(f"Connection error: {str(e)}")
            return False
    
    def disconnect(self):
        if self.connected and self.sock:
            self.sock.close()
            self.connected = False
            self.status_update.emit("Disconnected")
    
    def get_transaction_id(self):
        self.transaction_id = (self.transaction_id + 1) % 65536
        return self.transaction_id
    
    def read_object(self, index, subindex, size):
        if not self.connected or not self.sock:
            self.status_update.emit("Not connected")
            return None
            
        try:
            # Format according to section 6.6.5 of the manual
            tid = self.get_transaction_id()
            packet = bytearray([
                (tid >> 8) & 0xFF, tid & 0xFF,  # Transaction ID
                0x00, 0x00,  # Protocol ID
                0x00, 0x0D,  # Length
                0x00,        # Unit ID
                0x2B,        # Function code
                0x0D,        # MEI type
                0x00,        # Protocol option (0=read)
                0x00,        # Reserved
                0x00,        # Node ID
                (index >> 8) & 0xFF, index & 0xFF,  # Object Index
                subindex,    # Sub Index
                0x00, 0x00,  # Starting Address
                0x00,        # SDO Object
                size         # Byte count
            ])
            
            self.sock.send(packet)
            response = self.sock.recv(1024)
            
            # According to section 6.6.6, the data is in bytes 19+
            if len(response) >= 19 + size:
                value = 0
                for i in range(size):
                    value |= response[19 + i] << (8 * i)
                return value
            else:
                self.status_update.emit("Response too short")
                return None
                
        except Exception as e:
            self.status_update.emit(f"Error reading object: {str(e)}")
            return None
    
    def write_object(self, index, subindex, value, size):
        if not self.connected or not self.sock:
            self.status_update.emit("Not connected")
            return False
            
        try:
            # Format according to section 6.6.5 of the manual
            tid = self.get_transaction_id()
            packet = bytearray([
                (tid >> 8) & 0xFF, tid & 0xFF,  # Transaction ID
                0x00, 0x00,  # Protocol ID
                0x00, 0x0D + size,  # Length (13 + data size)
                0x00,        # Unit ID
                0x2B,        # Function code
                0x0D,        # MEI type
                0x01,        # Protocol option (1=write)
                0x00,        # Reserved
                0x00,        # Node ID
                (index >> 8) & 0xFF, index & 0xFF,  # Object Index
                subindex,    # Sub Index
                0x00, 0x00,  # Starting Address
                0x00,        # SDO Object
                size,        # Byte count
            ])
            
            # Add value in little endian format
            for i in range(size):
                packet.append((value >> (8 * i)) & 0xFF)
            
            self.sock.send(packet)
            response = self.sock.recv(1024)
            
            self.status_update.emit(f"Object 0x{index:04X}:{subindex} written with value {value}")
            return True
                
        except Exception as e:
            self.status_update.emit(f"Error writing object: {str(e)}")
            return False
    
    def read_statusword(self):
        value = self.read_object(0x6041, 0, 2)
        if value is not None:
            self.statusword_update.emit(value)
            self.status_update.emit(f"Statusword: 0x{value:04X}")
        return value
    
    def write_controlword(self, value):
        return self.write_object(0x6040, 0, value, 2)

class MotorControlGUI(QMainWindow):
    def __init__(self):
        super().__init__()
        self.gateway = ModbusTCPGateway()
        self.status_timer = QTimer()
        self.status_timer.timeout.connect(self.update_status)
        
        self.init_ui()
        
    def init_ui(self):
        self.setWindowTitle('Dryve D1 Motor Control')
        self.setGeometry(100, 100, 800, 600)
        
        main_widget = QWidget()
        main_layout = QVBoxLayout()
        
        # Connection group
        connection_group = QGroupBox("Connection")
        connection_layout = QHBoxLayout()
        
        self.ip_input = QLineEdit("169.254.239.1")
        self.port_input = QLineEdit("502")
        self.connect_btn = QPushButton("Connect")
        self.connect_btn.clicked.connect(self.toggle_connection)
        
        connection_layout.addWidget(QLabel("IP:"))
        connection_layout.addWidget(self.ip_input)
        connection_layout.addWidget(QLabel("Port:"))
        connection_layout.addWidget(self.port_input)
        connection_layout.addWidget(self.connect_btn)
        connection_group.setLayout(connection_layout)
        
        # State machine group
        state_group = QGroupBox("State Machine")
        state_layout = QGridLayout()
        
        self.shutdown_btn = QPushButton("Shutdown")
        self.shutdown_btn.clicked.connect(lambda: self.gateway.write_controlword(0x0006))
        
        self.switch_on_btn = QPushButton("Switch On")
        self.switch_on_btn.clicked.connect(lambda: self.gateway.write_controlword(0x0007))
        
        self.enable_operation_btn = QPushButton("Enable Operation")
        self.enable_operation_btn.clicked.connect(lambda: self.gateway.write_controlword(0x000F))
        
        self.state_label = QLabel("Current State: Unknown")
        
        state_layout.addWidget(self.shutdown_btn, 0, 0)
        state_layout.addWidget(self.switch_on_btn, 0, 1)
        state_layout.addWidget(self.enable_operation_btn, 0, 2)
        state_layout.addWidget(self.state_label, 1, 0, 1, 3)
        state_group.setLayout(state_layout)
        
        # Movement group
        movement_group = QGroupBox("Movement Control")
        movement_layout = QGridLayout()
        
        self.position_input = QSpinBox()
        self.position_input.setRange(-1000000, 1000000)
        self.position_input.setValue(1000)
        
        self.velocity_input = QSpinBox()
        self.velocity_input.setRange(0, 100000)
        self.velocity_input.setValue(1000)
        
        self.acceleration_input = QSpinBox()
        self.acceleration_input.setRange(0, 100000)
        self.acceleration_input.setValue(2000)
        
        self.move_btn = QPushButton("Move to Position")
        self.move_btn.clicked.connect(self.start_movement)
        
        self.stop_btn = QPushButton("Stop")
        self.stop_btn.clicked.connect(lambda: self.gateway.write_controlword(0x000F))
        
        self.home_btn = QPushButton("Home")
        self.home_btn.clicked.connect(self.start_homing)
        
        movement_layout.addWidget(QLabel("Position:"), 0, 0)
        movement_layout.addWidget(self.position_input, 0, 1)
        movement_layout.addWidget(QLabel("Velocity:"), 1, 0)
        movement_layout.addWidget(self.velocity_input, 1, 1)
        movement_layout.addWidget(QLabel("Acceleration:"), 2, 0)
        movement_layout.addWidget(self.acceleration_input, 2, 1)
        movement_layout.addWidget(self.move_btn, 0, 2)
        movement_layout.addWidget(self.stop_btn, 1, 2)
        movement_layout.addWidget(self.home_btn, 2, 2)
        movement_group.setLayout(movement_layout)
        
        # Log area
        log_group = QGroupBox("Log")
        log_layout = QVBoxLayout()
        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        log_layout.addWidget(self.log_text)
        log_group.setLayout(log_layout)
        
        # Add all components to main layout
        main_layout.addWidget(connection_group)
        main_layout.addWidget(state_group)
        main_layout.addWidget(movement_group)
        main_layout.addWidget(log_group)
        
        main_widget.setLayout(main_layout)
        self.setCentralWidget(main_widget)
        
        # Connect signals
        self.gateway.status_update.connect(self.log_message)
        self.gateway.statusword_update.connect(self.update_state_display)
        
        # Initially disable controls
        self.toggle_controls(False)
        
    def toggle_connection(self):
        if not self.gateway.connected:
            ip = self.ip_input.text()
            port = int(self.port_input.text())
            if self.gateway.connect(ip, port):
                self.connect_btn.setText("Disconnect")
                self.toggle_controls(True)
                self.status_timer.start(1000)  # Update status every second
        else:
            self.gateway.disconnect()
            self.connect_btn.setText("Connect")
            self.toggle_controls(False)
            self.status_timer.stop()
    
    def toggle_controls(self, enabled):
        self.shutdown_btn.setEnabled(enabled)
        self.switch_on_btn.setEnabled(enabled)
        self.enable_operation_btn.setEnabled(enabled)
        self.move_btn.setEnabled(enabled)
        self.stop_btn.setEnabled(enabled)
        self.home_btn.setEnabled(enabled)
        self.position_input.setEnabled(enabled)
        self.velocity_input.setEnabled(enabled)
        self.acceleration_input.setEnabled(enabled)
    
    def update_status(self):
        if self.gateway.connected:
            self.gateway.read_statusword()
    
    def update_state_display(self, statusword):
        state = "Unknown"
        if (statusword & 0x6F) == 0x00:
            state = "Not ready to switch on"
        elif (statusword & 0x6F) == 0x40:
            state = "Switch on disabled"
        elif (statusword & 0x6F) == 0x21:
            state = "Ready to switch on"
        elif (statusword & 0x6F) == 0x23:
            state = "Switched on"
        elif (statusword & 0x6F) == 0x27:
            state = "Operation enabled"
        elif (statusword & 0x6F) == 0x07:
            state = "Quick stop active"
        elif (statusword & 0x6F) == 0x0F:
            state = "Fault reaction active"
        elif (statusword & 0x6F) == 0x08:
            state = "Fault"
            
        self.state_label.setText(f"Current State: {state}")
    
    def log_message(self, message):
        self.log_text.append(message)
        self.log_text.ensureCursorVisible()
    
    def start_movement(self):
        # Set operation mode to Profile Position (1)
        self.gateway.write_object(0x6060, 0, 1, 1)
        time.sleep(0.1)
        
        # Set target position
        position = self.position_input.value()
        self.gateway.write_object(0x607A, 0, position, 4)
        time.sleep(0.1)
        
        # Set profile velocity
        velocity = self.velocity_input.value()
        self.gateway.write_object(0x6081, 0, velocity, 4)
        time.sleep(0.1)
        
        # Set profile acceleration
        acceleration = self.acceleration_input.value()
        self.gateway.write_object(0x6083, 0, acceleration, 4)
        time.sleep(0.1)
        
        # Start the movement (bit 4 set to 1)
        self.gateway.write_controlword(0x001F)
    
    def start_homing(self):
        # Set operation mode to Homing (6)
        self.gateway.write_object(0x6060, 0, 6, 1)
        time.sleep(0.1)
        
        # Set homing method (depends on your setup)
        self.gateway.write_object(0x6098, 0, 33, 1)  # Method 33 = index pulse negative direction
        time.sleep(0.1)
        
        # Set homing speeds
        self.gateway.write_object(0x6099, 1, 1000, 4)  # Search velocity
        self.gateway.write_object(0x6099, 2, 500, 4)   # Zero velocity
        time.sleep(0.1)
        
        # Set homing acceleration
        self.gateway.write_object(0x609A, 0, 2000, 4)
        time.sleep(0.1)
        
        # Start homing (bit 4 set to 1)
        self.gateway.write_controlword(0x001F)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MotorControlGUI()
    window.show()
    sys.exit(app.exec_())
