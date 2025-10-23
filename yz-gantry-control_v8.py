"""
YZ Gantry Control with Arrow Keys

This program allows control of a YZ gantry system using keyboard arrow keys.
It communicates with two dryve D1 motor controllers over standard Modbus TCP protocol.

- Left/Right arrows: Control Y-axis movement
- Up/Down arrows: Control Z-axis movement

Author: Claude
Date: April 30, 2025
"""

import tkinter as tk
import time
import logging
from pymodbus.client import ModbusTcpClient
from pymodbus.constants import Endian
from pymodbus.payload import BinaryPayloadBuilder, BinaryPayloadDecoder

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("gantry_control")

# Motor controller IP addresses
Y_CONTROLLER_IP = "169.254.239.1"
Z_CONTROLLER_IP = "169.254.239.2"
MODBUS_PORT = 502

# Register addresses for motor control
# These may need adjustment based on your specific dryve D1 configuration
REG_CONTROL = 0      # Control register
REG_STATUS = 1       # Status register
REG_TARGET_POS = 2   # Target position register
REG_ACTUAL_POS = 4   # Actual position register
REG_SPEED = 6        # Speed register
REG_ACCEL = 8        # Acceleration register
REG_DECEL = 10       # Deceleration register
REG_OP_MODE = 12     # Operation mode register

# Control register bits
CTRL_START = 0x0001      # Start bit
CTRL_STOP = 0x0002       # Stop bit
CTRL_RESET = 0x0004      # Reset bit
CTRL_JOG_POS = 0x0008    # Jog positive direction
CTRL_JOG_NEG = 0x0010    # Jog negative direction
CTRL_ENABLE = 0x0020     # Enable motor
CTRL_HOME = 0x0040       # Home command

# Status register bits
STATUS_READY = 0x0001    # Ready bit
STATUS_RUNNING = 0x0002  # Running bit
STATUS_ERROR = 0x0004    # Error bit
STATUS_HOMED = 0x0008    # Homed bit

# Operation modes
MODE_POSITION = 1        # Position mode
MODE_VELOCITY = 2        # Velocity mode
MODE_JOG = 3             # Jog mode

# Movement parameters
JOG_DISTANCE = 10    # Distance to move in mm for each key press
JOG_VELOCITY = 50    # Velocity in mm/s
JOG_ACCELERATION = 200    # Acceleration in mm/s²
JOG_DECELERATION = 200    # Deceleration in mm/s²

class ModbusMotorController:
    """
    Client for standard Modbus TCP communication with dryve D1 controller.
    """
    def __init__(self, ip_address, port=502):
        self.ip_address = ip_address
        self.port = port
        self.client = ModbusTcpClient(host=ip_address, port=port)
        self.connected = False
        
    def connect(self):
        """Connect to the controller"""
        try:
            self.connected = self.client.connect()
            if self.connected:
                logger.info(f"Connected to motor controller at {self.ip_address}")
            else:
                logger.error(f"Failed to connect to motor controller at {self.ip_address}")
            return self.connected
        except Exception as e:
            logger.error(f"Error connecting to {self.ip_address}: {e}")
            self.connected = False
            return False
        
    def disconnect(self):
        """Disconnect from the controller"""
        if self.connected:
            self.client.close()
            self.connected = False
            logger.info(f"Disconnected from motor controller at {self.ip_address}")
    
    def read_register(self, address, count=1):
        """Read holding registers from the controller"""
        if not self.connected:
            return None
        
        try:
            result = self.client.read_holding_registers(address, count)
            if result.isError():
                logger.error(f"Error reading registers at address {address}: {result}")
                return None
            return result.registers
        except Exception as e:
            logger.error(f"Error reading registers at address {address}: {e}")
            return None
    
    def write_register(self, address, value):
        """Write a single value to a holding register"""
        if not self.connected:
            return False
        
        try:
            result = self.client.write_register(address, value)
            if result.isError():
                logger.error(f"Error writing to register at address {address}: {result}")
                return False
            return True
        except Exception as e:
            logger.error(f"Error writing to register at address {address}: {e}")
            return False
    
    def write_registers(self, address, values):
        """Write multiple values to holding registers"""
        if not self.connected:
            return False
        
        try:
            result = self.client.write_registers(address, values)
            if result.isError():
                logger.error(f"Error writing to registers at address {address}: {result}")
                return False
            return True
        except Exception as e:
            logger.error(f"Error writing to registers at address {address}: {e}")
            return False
    
    def initialize_motor(self):
        """Initialize the motor controller"""
        # Enable the motor
        if not self.write_register(REG_CONTROL, CTRL_ENABLE):
            logger.error("Failed to enable motor")
            return False
        
        # Set operation mode to position mode
        if not self.write_register(REG_OP_MODE, MODE_POSITION):
            logger.error("Failed to set operation mode")
            return False
            
        # Set default movement parameters
        if not self.write_register(REG_SPEED, JOG_VELOCITY):
            logger.error("Failed to set default speed")
            return False
            
        if not self.write_register(REG_ACCEL, JOG_ACCELERATION):
            logger.error("Failed to set default acceleration")
            return False
            
        if not self.write_register(REG_DECEL, JOG_DECELERATION):
            logger.error("Failed to set default deceleration")
            return False
        
        # Check if motor is ready
        status = self.read_register(REG_STATUS)
        if status and (status[0] & STATUS_READY):
            logger.info("Motor initialized successfully and ready")
            return True
        else:
            logger.error("Motor initialization failed or motor not ready")
            return False
    
    def move_relative(self, distance):
        """Move motor by a relative distance"""
        if not self.connected:
            return False
        
        # Set movement parameters
        if not self.write_register(REG_SPEED, JOG_VELOCITY):
            return False
            
        if not self.write_register(REG_ACCEL, JOG_ACCELERATION):
            return False
            
        if not self.write_register(REG_DECEL, JOG_DECELERATION):
            return False
        
        # Set target position (relative to current position)
        current_pos = self.get_actual_position()
        if current_pos is not None:
            target_pos = current_pos + distance
            if not self.write_register(REG_TARGET_POS, target_pos):
                return False
        else:
            return False
        
        # Start movement
        if not self.write_register(REG_CONTROL, CTRL_START | CTRL_ENABLE):
            return False
            
        return True
    
    def get_actual_position(self):
        """Get the actual position of the motor"""
        result = self.read_register(REG_ACTUAL_POS)
        if result:
            return result[0]
        return None
    
    def is_ready(self):
        """Check if the motor is ready for commands"""
        status = self.read_register(REG_STATUS)
        if status:
            return (status[0] & STATUS_READY) != 0
        return False
    
    def is_moving(self):
        """Check if the motor is currently moving"""
        status = self.read_register(REG_STATUS)
        if status:
            return (status[0] & STATUS_RUNNING) != 0
        return False

class GantryControl:
    """Main class for gantry control with GUI"""
    def __init__(self, master):
        self.master = master
        master.title("YZ Gantry Control")
        
        # Set up the UI
        self.status_label = tk.Label(master, text="Initializing...", font=("Arial", 12))
        self.status_label.pack(pady=10)
        
        self.position_frame = tk.Frame(master)
        self.position_frame.pack(pady=10)
        
        self.y_pos_label = tk.Label(self.position_frame, text="Y Position: ---", font=("Arial", 10), width=15, anchor="w")
        self.y_pos_label.grid(row=0, column=0, padx=10)
        
        self.z_pos_label = tk.Label(self.position_frame, text="Z Position: ---", font=("Arial", 10), width=15, anchor="w")
        self.z_pos_label.grid(row=0, column=1, padx=10)
        
        self.keys_frame = tk.Frame(master)
        self.keys_frame.pack(pady=20)
        
        # Create a visual representation of arrow keys
        self.up_button = tk.Button(self.keys_frame, text="↑", font=("Arial", 16), width=3, height=1)
        self.up_button.grid(row=0, column=1, padx=5, pady=5)
        
        self.left_button = tk.Button(self.keys_frame, text="←", font=("Arial", 16), width=3, height=1)
        self.left_button.grid(row=1, column=0, padx=5, pady=5)
        
        self.down_button = tk.Button(self.keys_frame, text="↓", font=("Arial", 16), width=3, height=1)
        self.down_button.grid(row=1, column=1, padx=5, pady=5)
        
        self.right_button = tk.Button(self.keys_frame, text="→", font=("Arial", 16), width=3, height=1)
        self.right_button.grid(row=1, column=2, padx=5, pady=5)
        
        self.help_label = tk.Label(master, text="Use arrow keys to move the gantry", font=("Arial", 10))
        self.help_label.pack(pady=10)
        
        # Initialize motor controllers
        self.y_controller = ModbusMotorController(Y_CONTROLLER_IP, MODBUS_PORT)
        self.z_controller = ModbusMotorController(Z_CONTROLLER_IP, MODBUS_PORT)
        
        # Connect to motors
        self.connect_to_motors()
        
        # Bind arrow key events
        self.master.bind("<Left>", self.move_left)
        self.master.bind("<Right>", self.move_right)
        self.master.bind("<Up>", self.move_up)
        self.master.bind("<Down>", self.move_down)
        
        # Start position update timer
        self.update_position()
        
        # Set up cleanup on window close
        self.master.protocol("WM_DELETE_WINDOW", self.on_closing)
    
    def connect_to_motors(self):
        """Connect to motor controllers and initialize them"""
        self.status_label.config(text="Connecting to controllers...")
        self.master.update()
        
        y_connected = self.y_controller.connect()
        z_connected = self.z_controller.connect()
        
        if y_connected and z_connected:
            self.status_label.config(text="Connected to controllers. Initializing motors...")
            self.master.update()
            
            y_initialized = self.y_controller.initialize_motor()
            z_initialized = self.z_controller.initialize_motor()
            
            if y_initialized and z_initialized:
                self.status_label.config(text="System ready")
            else:
                self.status_label.config(text="Failed to initialize motors")
        else:
            self.status_label.config(text="Failed to connect to controllers")
    
    def update_position(self):
        """Update position display"""
        if self.y_controller.connected and self.z_controller.connected:
            y_pos = self.y_controller.get_actual_position()
            z_pos = self.z_controller.get_actual_position()
            
            if y_pos is not None:
                self.y_pos_label.config(text=f"Y Position: {y_pos}")
            if z_pos is not None:
                self.z_pos_label.config(text=f"Z Position: {z_pos}")
        
        # Schedule next update
        self.master.after(500, self.update_position)
    
    def move_left(self, event=None):
        """Move Y axis in negative direction"""
        self.flash_button(self.left_button)
        if self.y_controller.connected and self.y_controller.is_ready():
            self.y_controller.move_relative(-JOG_DISTANCE)
    
    def move_right(self, event=None):
        """Move Y axis in positive direction"""
        self.flash_button(self.right_button)
        if self.y_controller.connected and self.y_controller.is_ready():
            self.y_controller.move_relative(JOG_DISTANCE)
    
    def move_up(self, event=None):
        """Move Z axis in positive direction"""
        self.flash_button(self.up_button)
        if self.z_controller.connected and self.z_controller.is_ready():
            self.z_controller.move_relative(JOG_DISTANCE)
    
    def move_down(self, event=None):
        """Move Z axis in negative direction"""
        self.flash_button(self.down_button)
        if self.z_controller.connected and self.z_controller.is_ready():
            self.z_controller.move_relative(-JOG_DISTANCE)
    
    def flash_button(self, button):
        """Visual feedback for button press"""
        original_color = button.cget("background")
        button.config(background="light blue")
        self.master.after(100, lambda: button.config(background=original_color))
    
    def on_closing(self):
        """Clean up resources on window close"""
        if self.y_controller.connected:
            self.y_controller.disconnect()
        if self.z_controller.connected:
            self.z_controller.disconnect()
        self.master.destroy()


if __name__ == "__main__":
    root = tk.Tk()
    app = GantryControl(root)
    root.geometry("400x300")
    root.mainloop()
