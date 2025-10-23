import socket
import time
import sys

# Motor controller IP addresses
Y_CONTROLLER_IP = "169.254.239.1"
Z_CONTROLLER_IP = "169.254.239.2"
MODBUS_PORT = 502

def create_connection(ip_address, port=MODBUS_PORT):
    """Create a socket connection to the motor controller"""
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(5)  # 5 second timeout
    
    try:
        print(f"Connecting to {ip_address}:{port}...")
        sock.connect((ip_address, port))
        print("Connected successfully!")
        return sock
    except Exception as e:
        print(f"Connection failed: {e}")
        return None

def read_statusword(sock):
    """Read the statusword (object 6041h) using the correct format from manual"""
    try:
        # Format according to section 6.6.5 of the manual
        packet = bytearray([
            0x00, 0x0F,  # Transaction ID
            0x00, 0x00,  # Protocol ID
            0x00, 0x0D,  # Length
            0x00,        # Unit ID
            0x2B,        # Function code
            0x0D,        # MEI type
            0x00,        # Protocol option (0=read)
            0x00,        # Reserved
            0x00,        # Node ID
            0x60, 0x41,  # Object Index (6041h)
            0x00,        # Sub Index
            0x00, 0x00,  # Starting Address
            0x00,        # SDO Object
            0x02         # Byte count
        ])
        
        sock.send(packet)
        response = sock.recv(1024)
        
        # According to section 6.6.6, the statusword should be in bytes 19-20 (little endian)
        if len(response) >= 21:
            statusword = response[19] | (response[20] << 8)
            print(f"Statusword: 0x{statusword:04X}")
            return statusword
        else:
            print("Response too short")
            return None
            
    except Exception as e:
        print(f"Error reading statusword: {e}")
        return None

def write_controlword(sock, value):
    """Write to the controlword (object 6040h)"""
    try:
        # Format according to section 6.6.5 of the manual
        packet = bytearray([
            0x00, 0x0F,  # Transaction ID
            0x00, 0x00,  # Protocol ID
            0x00, 0x0F,  # Length (15 bytes after byte 5)
            0x00,        # Unit ID
            0x2B,        # Function code
            0x0D,        # MEI type
            0x01,        # Protocol option (1=write)
            0x00,        # Reserved
            0x00,        # Node ID
            0x60, 0x40,  # Object Index (6040h)
            0x00,        # Sub Index
            0x00, 0x00,  # Starting Address
            0x00,        # SDO Object
            0x02,        # Byte count
            value & 0xFF, (value >> 8) & 0xFF  # Value (little endian)
        ])
        
        sock.send(packet)
        response = sock.recv(1024)
        
        return True
            
    except Exception as e:
        print(f"Error writing controlword: {e}")
        return False

def write_object(sock, index, sub_index, value, size):
    """Write to a CANopen object"""
    try:
        # Basic header
        packet = bytearray([
            0x00, 0x0F,  # Transaction ID
            0x00, 0x00,  # Protocol ID
            0x00, 0x0D + size,  # Length (13 + data size)
            0x00,        # Unit ID
            0x2B,        # Function code
            0x0D,        # MEI type
            0x01,        # Protocol option (1=write)
            0x00,        # Reserved
            0x00,        # Node ID
            (index >> 8) & 0xFF, index & 0xFF,  # Object Index 
            sub_index,   # Sub Index
            0x00, 0x00,  # Starting Address
            0x00,        # SDO Object
            size,        # Byte count
        ])
        
        # Add value in little endian format
        value_bytes = bytearray()
        for i in range(size):
            value_bytes.append((value >> (8*i)) & 0xFF)
        
        packet.extend(value_bytes)
        
        sock.send(packet)
        response = sock.recv(1024)
        
        print(f"Object 0x{index:04X}:{sub_index} written with value {value}")
        return True
            
    except Exception as e:
        print(f"Error writing object: {e}")
        return False

def go_through_state_machine(sock):
    """Go through the state machine to reach 'Operation Enabled' state"""
    # First check current status
    status = read_statusword(sock)
    if status is None:
        return False
    
    # Command: Shutdown (prepare for switch on)
    print("\nSending 'Shutdown' command...")
    write_controlword(sock, 0x0006)
    time.sleep(5)
    status = read_statusword(sock)
    
    # Command: Switch On
    print("\nSending 'Switch On' command...")
    write_controlword(sock, 0x0007)
    time.sleep(5)
    status = read_statusword(sock)
    
    # Command: Enable Operation
    print("\nSending 'Enable Operation' command...")
    write_controlword(sock, 0x000F)
    time.sleep(5)
    status = read_statusword(sock)
    
    # Check if we reached Operation Enabled state
    if status is not None and (status & 0x0627) == 0x0627:
        print("Successfully reached 'Operation Enabled' state")
        return True
    else:
        print("Failed to reach 'Operation Enabled' state")
        return False

def test_simple_movement(sock):
    """Test a simple movement in Profile Position mode"""
    # Set operation mode to Profile Position (1)
    print("\nSetting operation mode to Profile Position...")
    write_object(sock, 0x6060, 0, 1, 1)
    time.sleep(5)
    
    # Set target position (1000 increments)
    print("\nSetting target position to 1000...")
    write_object(sock, 0x607A, 0, 100000, 4)
    time.sleep(5)
    
    # Set profile velocity (1000 units/sec)
    print("\nSetting profile velocity to 1000...")
    write_object(sock, 0x6081, 0, 1000, 4)
    time.sleep(5)
    
    # Set profile acceleration (2000 units/sec²)
    print("\nSetting profile acceleration to 2000...")
    write_object(sock, 0x6083, 0, 2000, 4)
    time.sleep(5)
    
    # Start the movement (bit 4 set to 1)
    print("\nStarting movement...")
    write_controlword(sock, 0x001F)
    time.sleep(5)
    
    # Wait for movement to complete
    print("\nWaiting for movement to complete...")
    for _ in range(10):
        status = read_statusword(sock)
        if status is not None and (status & 0x0400):  # Check target reached bit
            print("Movement completed")
            break
        time.sleep(5)
    
    # Reset the start bit
    write_controlword(sock, 0x000F)
    
    # Return to start position
    print("\nSetting target position to 0...")
    write_object(sock, 0x607A, 0, 0, 4)
    time.sleep(5)
    
    # Start the movement
    print("\nReturning to start position...")
    write_controlword(sock, 0x001F)
    time.sleep(5)
    
    # Wait for movement to complete
    for _ in range(10):
        status = read_statusword(sock)
        if status is not None and (status & 0x0400):
            print("Return movement completed")
            break
        time.sleep(5)
    
    # Reset the start bit
    write_controlword(sock, 0x000F)

def test_both_axes_in_sync(y_sock, z_sock):
    """Test synchronized movement of both Y and Z axes"""
    # Set both controllers to Profile Position mode
    print("\nSetting both controllers to Profile Position mode...")
    write_object(y_sock, 0x6060, 0, 1, 1)
    write_object(z_sock, 0x6060, 0, 1, 1)
    time.sleep(5)
    
    # Set target positions
    print("\nSetting target positions...")
    write_object(y_sock, 0x607A, 0, 1000, 4)
    write_object(z_sock, 0x607A, 0, 1000, 4)
    time.sleep(5)
    
    # Set velocities
    print("\nSetting velocities...")
    write_object(y_sock, 0x6081, 0, 1000, 4)
    write_object(z_sock, 0x6081, 0, 1000, 4)
    time.sleep(5)
    
    # Set accelerations
    print("\nSetting accelerations...")
    write_object(y_sock, 0x6083, 0, 2000, 4)
    write_object(z_sock, 0x6083, 0, 2000, 4)
    time.sleep(5)
    
    # Start movements simultaneously
    print("\nStarting synchronized movement...")
    write_controlword(y_sock, 0x001F)
    write_controlword(z_sock, 0x001F)
    
    # Wait for movements to complete
    print("\nWaiting for movements to complete...")
    for _ in range(20):
        y_status = read_statusword(y_sock)
        z_status = read_statusword(z_sock)
        
        if (y_status is not None and (y_status & 0x0400)) and (z_status is not None and (z_status & 0x0400)):
            print("Both movements completed")
            break
        time.sleep(5)
    
    # Reset start bits
    write_controlword(y_sock, 0x000F)
    write_controlword(z_sock, 0x000F)
    
    # Return to start positions
    print("\nReturning to start positions...")
    write_object(y_sock, 0x607A, 0, 0, 4)
    write_object(z_sock, 0x607A, 0, 0, 4)
    time.sleep(5)
    
    # Start return movements
    write_controlword(y_sock, 0x001F)
    write_controlword(z_sock, 0x001F)
    
    # Wait for return movements to complete
    for _ in range(20):
        y_status = read_statusword(y_sock)
        z_status = read_statusword(z_sock)
        
        if (y_status is not None and (y_status & 0x0400)) and (z_status is not None and (z_status & 0x0400)):
            print("Both return movements completed")
            break
        time.sleep(5)
    
    # Reset start bits
    write_controlword(y_sock, 0x000F)
    write_controlword(z_sock, 0x000F)

def main():
    while True:
        print("\n========== Motor Controller Test Menu ==========")
        print("1) Test Y-axis controller")
        print("2) Test Z-axis controller")
        print("3) Test both controllers sequentially")
        print("4) Test synchronized movement")
        print("5) Exit")
        
        choice = input("Enter your choice (1-5): ")
        
        if choice == '1':
            y_sock = create_connection(Y_CONTROLLER_IP)
            if y_sock:
                try:
                    print("\n--- Testing Y-axis controller ---")
                    if go_through_state_machine(y_sock):
                        test_simple_movement(y_sock)
                finally:
                    y_sock.close()
                    
        elif choice == '2':
            z_sock = create_connection(Z_CONTROLLER_IP)
            if z_sock:
                try:
                    print("\n--- Testing Z-axis controller ---")
                    if go_through_state_machine(z_sock):
                        test_simple_movement(z_sock)
                finally:
                    z_sock.close()
                    
        elif choice == '3':
            y_sock = create_connection(Y_CONTROLLER_IP)
            z_sock = create_connection(Z_CONTROLLER_IP)
            
            if y_sock and z_sock:
                try:
                    print("\n--- Testing Y-axis controller ---")
                    if go_through_state_machine(y_sock):
                        test_simple_movement(y_sock)
                    
                    print("\n--- Testing Z-axis controller ---")
                    if go_through_state_machine(z_sock):
                        test_simple_movement(z_sock)
                finally:
                    if y_sock:
                        y_sock.close()
                    if z_sock:
                        z_sock.close()
                    
        elif choice == '4':
            y_sock = create_connection(Y_CONTROLLER_IP)
            z_sock = create_connection(Z_CONTROLLER_IP)
            
            if y_sock and z_sock:
                try:
                    print("\n--- Initializing Y-axis controller ---")
                    y_initialized = go_through_state_machine(y_sock)
                    
                    print("\n--- Initializing Z-axis controller ---")
                    z_initialized = go_through_state_machine(z_sock)
                    
                    if y_initialized and z_initialized:
                        print("\n--- Running synchronized movement test ---")
                        test_both_axes_in_sync(y_sock, z_sock)
                finally:
                    if y_sock:
                        y_sock.close()
                    if z_sock:
                        z_sock.close()
                    
        elif choice == '5':
            print("Exiting...")
            sys.exit(0)
            
        else:
            print("Invalid choice. Please enter a number between 1 and 5.")

if __name__ == "__main__":
    main()
