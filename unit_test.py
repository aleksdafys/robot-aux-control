import time
import struct
from pymodbus.client import ModbusTcpClient
from pymodbus.constants import Endian
from pymodbus.payload import BinaryPayloadBuilder

# Motor controller IP addresses
Y_CONTROLLER_IP = "169.254.239.1"
Z_CONTROLLER_IP = "169.254.239.2"
MODBUS_PORT = 502  # Default Modbus TCP port

def create_modbus_client(ip_address):
    """Create and connect to a Modbus TCP client"""
    client = ModbusTcpClient(ip_address, port=MODBUS_PORT)
    if client.connect():
        print(f"Connected to controller at {ip_address}")
        return client
    else:
        print(f"Failed to connect to controller at {ip_address}")
        return None

def read_statusword(client):
    """Read the statusword (object 6041h) to get controller status"""
    try:
        # For Modbus TCP Gateway, we need to use raw message
        # Reading CANopen object 6041h (Statusword)
        request = struct.pack('>HHHBBBBHBBHH', 
                              0,       # Transaction ID
                              0,       # Protocol ID
                              13,      # Length
                              0,       # Unit ID
                              43,      # Function Code (2Bh)
                              13,      # MEI Type (0Dh)
                              0,       # Protocol control (read)
                              0,       # Reserved and Node ID
                              0x6041,  # Object index (6041h)
                              0,       # Sub index
                              0,       # Starting address
                              2)       # Byte count
        
        client.socket.send(request)
        response = client.socket.recv(1024)
        
        # Check if response is valid
        if len(response) >= 21:  # Header + data
            # Extract statusword value (bytes 19-20, little endian)
            status_value = struct.unpack('<H', response[19:21])[0]
            print(f"Statusword: 0x{status_value:04X}")
            return status_value
        else:
            print("Invalid response length")
            return None
            
    except Exception as e:
        print(f"Error reading statusword: {e}")
        return None

def write_controlword(client, value):
    """Write to the controlword (object 6040h) to control the drive"""
    try:
        # Writing CANopen object 6040h (Controlword)
        request = struct.pack('>HHHBBBBHBBHH', 
                              0,       # Transaction ID
                              0,       # Protocol ID
                              15,      # Length
                              0,       # Unit ID
                              43,      # Function Code (2Bh)
                              13,      # MEI Type (0Dh)
                              1,       # Protocol control (write)
                              0,       # Reserved and Node ID
                              0x6040,  # Object index (6040h)
                              0,       # Sub index
                              0,       # Starting address
                              2)       # Byte count
              
        # Add the value to write (little endian)
        request += struct.pack('<H', value)
        
        client.socket.send(request)
        response = client.socket.recv(1024)
        
        # Check if response is valid
        if len(response) >= 13:  # Header
            print(f"Successfully wrote controlword: 0x{value:04X}")
            return True
        else:
            print("Invalid response length")
            return False
            
    except Exception as e:
        print(f"Error writing controlword: {e}")
        return False

def write_object(client, index, sub_index, value, size):
    """Write to a CANopen object with the specified size"""
    try:
        # Calculate proper message length based on data size
        msg_length = 13 + size
        
        # Build header
        request = struct.pack('>HHHBBBBHBB', 
                              0,             # Transaction ID
                              0,             # Protocol ID
                              msg_length,    # Length
                              0,             # Unit ID
                              43,            # Function Code (2Bh)
                              13,            # MEI Type (0Dh)
                              1,             # Protocol control (write)
                              0,             # Reserved and Node ID
                              index,         # Object index
                              sub_index,     # Sub index
                              0)             # Starting address
                              
        # Add the size
        request += struct.pack('>H', size)
        
        # Add the value to write in little endian format
        if size == 1:
            request += struct.pack('<B', value)
        elif size == 2:
            request += struct.pack('<H', value)
        elif size == 4:
            request += struct.pack('<I', value)
        
        client.socket.send(request)
        response = client.socket.recv(1024)
        
        # Check if response is valid
        if len(response) >= 13:  # Header
            print(f"Successfully wrote object 0x{index:04X}:{sub_index} with value {value}")
            return True
        else:
            print("Invalid response length")
            return False
            
    except Exception as e:
        print(f"Error writing object: {e}")
        return False

def go_through_state_machine(client):
    """Go through the state machine to reach 'Operation Enabled' state"""
    # First check current status
    status = read_statusword(client)
    if status is None:
        return False
    
    # Command: Shutdown (prepare for switch on)
    print("Sending 'Shutdown' command...")
    write_controlword(client, 0x0006)
    time.sleep(0.5)
    status = read_statusword(client)
    
    # Command: Switch On
    print("Sending 'Switch On' command...")
    write_controlword(client, 0x0007)
    time.sleep(0.5)
    status = read_statusword(client)
    
    # Command: Enable Operation
    print("Sending 'Enable Operation' command...")
    write_controlword(client, 0x000F)
    time.sleep(0.5)
    status = read_statusword(client)
    
    # Check if we reached Operation Enabled state
    if status & 0x0627 == 0x0627:  # Check relevant bits
        print("Successfully reached 'Operation Enabled' state")
        return True
    else:
        print("Failed to reach 'Operation Enabled' state")
        return False

def test_simple_movement(client):
    """Test a simple movement in Profile Position mode"""
    # Set operation mode to Profile Position (1)
    print("Setting operation mode to Profile Position...")
    write_object(client, 0x6060, 0, 1, 1)
    time.sleep(0.5)
    
    # Set target position (1000 increments)
    print("Setting target position to 1000...")
    write_object(client, 0x607A, 0, 1000, 4)
    time.sleep(0.5)
    
    # Set profile velocity (1000 units/sec)
    print("Setting profile velocity to 1000...")
    write_object(client, 0x6081, 0, 1000, 4)
    time.sleep(0.5)
    
    # Set profile acceleration (2000 units/sec²)
    print("Setting profile acceleration to 2000...")
    write_object(client, 0x6083, 0, 2000, 4)
    time.sleep(0.5)
    
    # Start the movement (bit 4 set to 1)
    print("Starting movement...")
    write_controlword(client, 0x001F)
    time.sleep(0.5)
    
    # Wait for movement to complete
    print("Waiting for movement to complete...")
    for _ in range(10):
        status = read_statusword(client)
        if status is not None and (status & 0x0400):  # Check target reached bit
            print("Movement completed")
            break
        time.sleep(0.5)
    
    # Reset the start bit
    write_controlword(client, 0x000F)
    
    # Return to start position
    # Set target position (0 increments)
    print("Setting target position to 0...")
    write_object(client, 0x607A, 0, 0, 4)
    time.sleep(0.5)
    
    # Start the movement
    print("Returning to start position...")
    write_controlword(client, 0x001F)
    time.sleep(0.5)
    
    # Wait for movement to complete
    print("Waiting for return movement to complete...")
    for _ in range(10):
        status = read_statusword(client)
        if status is not None and (status & 0x0400):  # Check target reached bit
            print("Return movement completed")
            break
        time.sleep(0.5)
    
    # Reset the start bit
    write_controlword(client, 0x000F)

def main():
    # Connect to both controllers
    y_client = create_modbus_client(Y_CONTROLLER_IP)
    z_client = create_modbus_client(Z_CONTROLLER_IP)
    
    if not (y_client and z_client):
        print("Failed to connect to one or both controllers. Exiting.")
        return
    
    try:
        # Select which controller to test
        while True:
            print("\nMotor Controller Test Menu:")
            print("1) Test Y-axis controller")
            print("2) Test Z-axis controller")
            print("3) Test both controllers sequentially")
            print("4) Exit")
            
            choice = input("Enter your choice (1-4): ")
            
            if choice == '1':
                print("\n--- Testing Y-axis controller ---")
                if go_through_state_machine(y_client):
                    test_simple_movement(y_client)
                    
            elif choice == '2':
                print("\n--- Testing Z-axis controller ---")
                if go_through_state_machine(z_client):
                    test_simple_movement(z_client)
                    
            elif choice == '3':
                print("\n--- Testing Y-axis controller ---")
                if go_through_state_machine(y_client):
                    test_simple_movement(y_client)
                
                print("\n--- Testing Z-axis controller ---")
                if go_through_state_machine(z_client):
                    test_simple_movement(z_client)
                    
            elif choice == '4':
                print("Exiting...")
                break
                
            else:
                print("Invalid choice. Please enter a number between 1 and 4.")
    
    finally:
        # Close connections
        if y_client:
            y_client.close()
        if z_client:
            z_client.close()
        print("Connections closed")

if __name__ == "__main__":
    main()
