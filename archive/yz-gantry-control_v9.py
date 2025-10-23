import tkinter as tk
import time
import struct
import socket
import logging

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

# Modbus function codes and MEI types for Gateway
MODBUS_CANOPEN_FUNCTION_CODE = 43  # 0x2B
MODBUS_CANOPEN_MEI_TYPE = 13       # 0x0D

# CANopen object indexes (from manual section 6.5.19)
CONTROLWORD_INDEX = 0x6040
STATUSWORD_INDEX = 0x6041
OPERATION_MODE_INDEX = 0x6060
OPERATION_MODE_DISPLAY_INDEX = 0x6061
TARGET_POSITION_INDEX = 0x607A
ACTUAL_POSITION_INDEX = 0x6064
PROFILE_VELOCITY_INDEX = 0x6081
PROFILE_ACCELERATION_INDEX = 0x6083
PROFILE_DECELERATION_INDEX = 0x6084

# Operation modes
PROFILE_POSITION_MODE = 1
PROFILE_VELOCITY_MODE = 3

# Controlword bit masks (from manual section 6.5.11)
CONTROLWORD_SHUTDOWN = 0x0006
CONTROLWORD_SWITCH_ON = 0x0007
CONTROLWORD_ENABLE_OPERATION = 0x000F
CONTROLWORD_HALT = 0x0100
CONTROLWORD_RELATIVE = 0x0040
CONTROLWORD_START_POSITIONING = 0x001F
CONTROLWORD_RESET_START = 0x000F

# Statusword bit masks (from manual section 6.5.10)
STATUSWORD_READY_TO_SWITCH_ON = 0x0001
STATUSWORD_SWITCHED_ON = 0x0003
STATUSWORD_OPERATION_ENABLED = 0x0007
STATUSWORD_TARGET_REACHED = 0x0400

# Movement parameters
JOG_DISTANCE = 10    # Distance to move in mm for each key press
JOG_VELOCITY = 50    # Velocity in mm/s
JOG_ACCELERATION = 200    # Acceleration in mm/s²
JOG_DECELERATION = 200    # Deceleration in mm/s²

class ModbusGatewayClient:
    """
    Client for Modbus TCP as gateway to CANopen protocol for dryve D1 controller.
    Implements section 6.6 of the dryve D1 manual for Modbus TCP Gateway.
    """
    def __init__(self, ip_address, port=502):
        self.ip_address = ip_address
        self.port = port
        self.transaction_id = 0
        self.connected = False
        
    def connect(self):
        """Test connection to the controller"""
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(2.0)
            sock.connect((self.ip_address, self.port))
            sock.close()
            self.connected = True
            logger.info(f"Connected to motor controller at {self.ip_address}")
            return True
        except Exception as e:
            self.connected = False
            logger.error(f"Failed to connect to motor controller at {self.ip_address}: {e}")
            return False
        
    def disconnect(self):
        """Disconnect from the controller"""
        self.connected = False
        logger.info(f"Disconnected from controller at {self.ip_address}")
        
    def read_object(self, index, subindex=0):
        """
        Read a CANopen object via Modbus TCP Gateway
        Following the protocol described in section 6.6.5 of the manual
        """
        if not self.connected:
            logger.error("Not connected to controller")
            return None
            
        # Increment transaction ID
        self.transaction_id = (self.transaction_id + 1) % 65536
        
        # Create Modbus TCP header
        header = struct.pack(
            '>HHHB',
            self.transaction_id,  # Transaction ID
            0,                    # Protocol ID (0 for Modbus)
            13,                   # Length (remaining bytes after this field)
            0                     # Unit ID
        )
        
        # Create Modbus data for CANopen gateway read
        data = struct.pack(
            'BBBBBBBBBBBB',
            MODBUS_CANOPEN_FUNCTION_CODE,  # Function code
            MODBUS_CANOPEN_MEI_TYPE,       # MEI type
            0,                             # Protocol option (0 = read)
            0,                             # Reserve
            0,                             # Node ID
            (index >> 8) & 0xFF,           # Object index high byte
            index & 0xFF,                  # Object index low byte
            subindex,                      # Subindex
            0, 0, 0, 0                     # Padding fields
        )
        
        # Combine header and data
        packet = header + data
        
        try:
            # Create socket and send packet
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(1.0)
            sock.connect((self.ip_address, self.port))
            sock.send(packet)
            
            # Receive response
            response = sock.recv(1024)
            sock.close()
            
            # Check if response is valid and has enough bytes
            if len(response) >= 21:
                # Check function code (bit 7 set indicates error)
                if response[7] == MODBUS_CANOPEN_FUNCTION_CODE:
                    # Extract 16-bit value (little endian as per manual)
                    value = struct.unpack('<H', response[19:21])[0]
                    logger.debug(f"Read object 0x{index:04X}:{subindex} = 0x{value:04X}")
                    return value
                else:
                    # Error response
                    error_code = response[8] if len(response) > 8 else -1
                    logger.error(f"Modbus error code: {error_code}")
            else:
                logger.error(f"Invalid response length: {len(response)}")
                
        except Exception as e:
            logger.error(f"Error reading object 0x{index:04X}:{subindex}: {e}")
        
        return None
    
    def write_object(self, index, subindex, data, data_size=2):
        """
        Write a CANopen object via Modbus TCP Gateway
        Following the protocol described in section 6.6.5 of the manual
        """
        if not self.connected:
            logger.error("Not connected to controller")
            return False
            
        # Increment transaction ID
        self.transaction_id = (self.transaction_id + 1) % 65536
        
        # Determine length based on data size
        length = 13 + data_size
        
        # Create Modbus TCP header
        header = struct.pack(
            '>HHHB',
            self.transaction_id,  # Transaction ID
            0,                    # Protocol ID (0 for Modbus)
            length,               # Length (remaining bytes after this field)
            0                     # Unit ID
        )
        
        # Create Modbus data header for CANopen gateway write
        data_header = struct.pack(
            'BBBBBBBBBBBB',
            MODBUS_CANOPEN_FUNCTION_CODE,  # Function code
            MODBUS_CANOPEN_MEI_TYPE,       # MEI type
            1,                             # Protocol option (1 = write)
            0,                             # Reserve
            0,                             # Node ID
            (index >> 8) & 0xFF,           # Object index high byte
            index & 0xFF,                  # Object index low byte
            subindex,                      # Subindex
            0, 0, 0,                       # Padding fields
            data_size                      # Data size
        )
        
        # Pack data according to size (little endian as per manual)
        if data_size == 1:
            data_bytes = struct.pack('<B', data & 0xFF)
        elif data_size == 2:
            data_bytes = struct.pack('<H', data & 0xFFFF)
        elif data_size == 4:
            data_bytes = struct.pack('<I', data & 0xFFFFFFFF)
        else:
            logger.error(f"Unsupported data size: {data_size}")
            return False
        
        # Combine all parts
        packet = header + data_header + data_bytes
        
        try:
            # Create socket and send packet
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(1.0)
            sock.connect((self.ip_address, self.port))
            sock.send(packet)
            
            # Receive response
            response = sock.recv(1024)
            sock.close()
            
            # Check response
            if len(response) >= 8:
                # Check function code (bit 7 set indicates error)
                if response[7] == MODBUS_CANOPEN_FUNCTION_CODE:
                    logger.debug(f"Write object 0x{index:04X}:{subindex} = 0x{data:X} successful")
                    return True
                else:
                    # Error response
                    error_code = response[8] if len(response) > 8 else -1
                    logger.error(f"Modbus error code: {error_code}")
            else:
                logger.error(f"Invalid response length: {len(response)}")
                
        except Exception as e:
            logger.error(f"Error writing object 0x{index:04X}:{subindex} = {data}: {e}")
        
        return False
    
    def initialize_motor(self):
        """
        Initialize the motor state machine to operation enabled state
        Following the state machine described in section 6.5.9 of the manual
        """
        logger.info(f"Initializing motor at {self.ip_address}")
        
        # Set operation mode to Profile Position
        if not self.write_object(OPERATION_MODE_INDEX, 0, PROFILE_POSITION_MODE, 1):
            logger.error("Failed to set operation mode")
            return False
        
        # Read statusword to check current state
        status = self.read_object(STATUSWORD_INDEX, 0)
        if status is None:
            logger.error("Failed to read status")
            return False
            
        logger.info(f"Initial status: 0x{status:04X}")
        
        # State machine transition: Shutdown
        logger.info("Sending Shutdown command")
        if not self.write_object(CONTROLWORD_INDEX, 0, CONTROLWORD_SHUTDOWN, 2):
            logger.error("Failed to send Shutdown command")
            return False
        time.sleep(0.1)
        
        # State machine transition: Switch On
        logger.info("Sending Switch On command")
        if not self.write_object(CONTROLWORD_INDEX, 0, CONTROLWORD_SWITCH_ON, 2):
            logger.error("Failed to send Switch On command")
            return False
        time.sleep(0.1)
        
        # State machine transition: Enable Operation
        logger.info("Sending Enable Operation command")
        if not self.write_object(CONTROLWORD_INDEX, 0, CONTROLWORD_ENABLE_OPERATION, 2):
            logger.error("Failed to send Enable Operation command")
            return False
        time.sleep(0.1)
        
        # Check if operation enabled
        status = self.read_object(STATUSWORD_INDEX, 0)
        if status is not None:
            logger.info(f"Final status: 0x{status:04X}")
            # According to manual, operation enabled state has bits 0, 1, 2 set (value 0x0007)
            # But bit 9 (0x0200) is also set if DI7 is set
            if (status & 0x0007) == 0x0007:
                logger.info("Motor initialized successfully and operation enabled")
                return True
            else:
                logger.error(f"Motor not in operation enabled state. Status: 0x{status:04X}")
                return False
        else:
            logger.error("Failed to read status after initialization")
            return False
    
    def move_relative(self, distance, velocity=JOG_VELOCITY, acceleration=JOG_ACCELERATION, deceleration=JOG_DECELERATION):
        """
        Move motor relative distance with specified parameters
        Using Profile Position Mode with relative positioning as described in section 6.5.13
        """
        logger.info(f"Moving motor at {self.ip_address} by {distance} units")
        
        # Set profile parameters
        if not self.write_object(PROFILE_VELOCITY_INDEX, 0, velocity, 4):
            logger.error("Failed to set velocity")
            return False
            
        if not self.write_object(PROFILE_ACCELERATION_INDEX, 0, acceleration, 4):
            logger.error("Failed to set acceleration")
            return False
            
        if not self.write_object(PROFILE_DECELERATION_INDEX, 0, deceleration, 4):
            logger.error("Failed to set deceleration")
            return False
        
        # Set target position (relative)
        if not self.write_object(TARGET_POSITION_INDEX, 0, distance, 4):
            logger.error("Failed to set target position")
            return False
        
        # Start movement (relative positioning)
        # Set bit 6 for relative positioning and bit 4 for start
        if not self.write_object(CONTROLWORD_INDEX, 0, CONTROLWORD_ENABLE_OPERATION | CONTROLWORD_RELATIVE | 0x0010, 2):
            logger.error("Failed to start movement")
            return False
        time.sleep(0.1)
        
        # Reset start bit
        if not self.write_object(CONTROLWORD_INDEX, 0, CONTROLWORD_ENABLE_OPERATION | CONTROLWORD_RELATIVE, 2):
            logger.error("Failed to reset start bit")
            return False
        
        return True
    
    def is_target_reached(self):
        """Check if target position has been reached"""
        status = self.read_object(STATUSWORD_INDEX, 0)
        if status is not None:
            # Bit 10 indicates target reached
            return (status & STATUSWORD_TARGET_REACHED) != 0
        return False
    
    def get_actual_position(self):
        """Get actual position of the motor"""
        return self.read_object(ACTUAL_POSITION_INDEX, 0)
    
    def is_ready(self):
        """Check if motor is ready for commands"""
        status = self.read_object(STATUSWORD_INDEX, 0)
        if status is not None:
            # Operation enabled state has bits 0, 1, 2 set
            return (status & 0x0007) == 0x0007
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
        self.y_controller = ModbusGatewayClient(Y_CONTROLLER_IP, MODBUS_PORT)
        self.z_controller = ModbusGatewayClient(Z_CONTROLLER_IP, MODBUS_PORT)
        
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
        self.y_controller.disconnect()
        self.z_controller.disconnect()
        self.master.destroy()


if __name__ == "__main__":
    root = tk.Tk()
    app = GantryControl(root)
    root.geometry("400x300")
    root.mainloop()
