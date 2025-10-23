import socket
import time
import sys
import binascii  # For better hex display of packets

# Motor controller IP addresses
Y_CONTROLLER_IP = "169.254.239.1"
Z_CONTROLLER_IP = "169.254.239.2"
MODBUS_PORT = 502

# Define state machine states for better tracking
STATE_NOT_READY = 0
STATE_SWITCH_ON_DISABLED = 1
STATE_READY_TO_SWITCH_ON = 2
STATE_SWITCHED_ON = 3
STATE_OPERATION_ENABLED = 4
STATE_FAULT = 5
STATE_UNKNOWN = 6

STATE_NAMES = {
    STATE_NOT_READY: "Not Ready to Switch On",
    STATE_SWITCH_ON_DISABLED: "Switch On Disabled",
    STATE_READY_TO_SWITCH_ON: "Ready to Switch On",
    STATE_SWITCHED_ON: "Switched On",
    STATE_OPERATION_ENABLED: "Operation Enabled",
    STATE_FAULT: "Fault",
    STATE_UNKNOWN: "Unknown State"
}

def decode_statusword(statusword):
    """Decode statusword to human-readable state based on Section 6.5.10 of manual"""
    state = STATE_UNKNOWN
    
    # Extract state bits according to manual
    if (statusword & 0x004F) == 0x0000:  # xxxx xxxx x0xx 0000
        state = STATE_NOT_READY
    elif (statusword & 0x004F) == 0x0040:  # xxxx xxxx x1xx 0000
        state = STATE_SWITCH_ON_DISABLED
    elif (statusword & 0x006F) == 0x0021:  # xxxx xxxx x01x 0001
        state = STATE_READY_TO_SWITCH_ON
    elif (statusword & 0x006F) == 0x0023:  # xxxx xxxx x01x 0011
        state = STATE_SWITCHED_ON
    elif (statusword & 0x006F) == 0x0027:  # xxxx xxxx x01x 0111
        state = STATE_OPERATION_ENABLED
    elif (statusword & 0x004F) == 0x0008:  # xxxx xxxx x0xx 1000
        state = STATE_FAULT
    
    description = STATE_NAMES.get(state, "Unknown State")
    result = f"State: {description} (0x{statusword:04X})"
    
    # Additional flags
    if statusword & 0x0080:
        result += ", Warning"
    if statusword & 0x0400:
        result += ", Target Reached"
    if statusword & 0x0200:
        result += ", Remote (DI7=1)"
    else:
        result += ", NOT Remote (DI7=0) - ENABLE IS OFF!"
    if statusword & 0x0800:
        result += ", Internal Limit Active"
    
    return result

def print_packet(packet, is_send=True):
    """Print packet in readable format for debugging"""
    direction = "SEND" if is_send else "RECV"
    print(f"{direction} Packet ({len(packet)} bytes):")
    print(f"  Hex: {binascii.hexlify(packet).decode()}")
    
    if len(packet) >= 18:  # Ensure we have enough bytes for basic parsing
        if is_send:
            print(f"  Transaction ID: 0x{packet[0]:02X}{packet[1]:02X}")
            print(f"  Protocol ID: 0x{packet[2]:02X}{packet[3]:02X}")
            print(f"  Length: {packet[4]:02X}{packet[5]:02X}")
            print(f"  Unit ID: {packet[6]:02X}")
            print(f"  Function code: 0x{packet[7]:02X}")
            print(f"  MEI type: 0x{packet[8]:02X}")
            print(f"  Protocol option: {packet[9]:02X} ({['Read', 'Write'][packet[9]]})")
            
            if packet[9] == 0:  # Read
                print(f"  Object: 0x{packet[12]:02X}{packet[13]:02X}:{packet[14]:02X}")
                print(f"  Byte count: {packet[18]:02X}")
            elif packet[9] == 1 and len(packet) > 19:  # Write
                print(f"  Object: 0x{packet[12]:02X}{packet[13]:02X}:{packet[14]:02X}")
                print(f"  Byte count: {packet[18]:02X}")
                data = int.from_bytes(packet[19:19+packet[18]], byteorder='little')
                print(f"  Data: 0x{data:X} ({data})")
        else:
            # Response packet parsing
            if packet[7] & 0x80:  # Error response
                print(f"  ERROR RESPONSE: Function code: 0x{packet[7]:02X}")
                if len(packet) > 8:
                    print(f"  Exception code: 0x{packet[8]:02X}")
            else:
                if len(packet) >= 21 and packet[7] == 0x2B:  # Standard response
                    print(f"  Response Function code: 0x{packet[7]:02X}")
                    print(f"  MEI type: 0x{packet[8]:02X}")
                    print(f"  Protocol option: {packet[9]:02X} ({['Read', 'Write'][packet[9]]})")
                    
                    if packet[9] == 0 and packet[18] > 0:  # Read response
                        data_length = packet[18]
                        if 19 + data_length <= len(packet):
                            data = int.from_bytes(packet[19:19+data_length], byteorder='little')
                            print(f"  Data: 0x{data:X} ({data})")
                            
                            if packet[12] == 0x60 and packet[13] == 0x41:  # Statusword
                                print(f"  {decode_statusword(data)}")

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
    """Read the statusword (object 6041h) using the format from manual"""
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
        
        print_packet(packet, True)
        sock.send(packet)
        
        response = sock.recv(1024)
        print_packet(response, False)
        
        # According to section 6.6.6, the statusword should be in bytes 19-20 (little endian)
        if len(response) >= 21:
            statusword = response[19] | (response[20] << 8)
            print(f"Statusword: 0x{statusword:04X}")
            print(decode_statusword(statusword))
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
        
        print(f"Writing controlword: 0x{value:04X} - {interpret_controlword(value)}")
        print_packet(packet, True)
        sock.send(packet)
        
        response = sock.recv(1024)
        print_packet(response, False)
        
        return True
            
    except Exception as e:
        print(f"Error writing controlword: {e}")
        return False

def interpret_controlword(value):
    """Translate controlword bits to human-readable form"""
    result = []
    
    if value & 0x0001:
        result.append("Switch On")
    if value & 0x0002:
        result.append("Enable Voltage")
    if value & 0x0004:
        result.append("Quick-Stop")
    if value & 0x0008:
        result.append("Enable Operation")
    if value & 0x0010:
        result.append("Start/Homing")
    if value & 0x0020:
        result.append("Apply Parameters")
    if value & 0x0040:
        result.append("Relative/Absolute")
    if value & 0x0080:
        result.append("Fault Reset")
    if value & 0x0100:
        result.append("Halt")
    
    return ", ".join(result)

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
        
        print(f"Writing object 0x{index:04X}:{sub_index} with value {value} (0x{value:X})")
        print_packet(packet, True)
        sock.send(packet)
        
        response = sock.recv(1024)
        print_packet(response, False)
        
        if response[7] & 0x80:
            print(f"ERROR: Failed to write object 0x{index:04X}:{sub_index}")
            return False
            
        print(f"Object 0x{index:04X}:{sub_index} written with value {value}")
        return True
            
    except Exception as e:
        print(f"Error writing object: {e}")
        return False

def read_object(sock, index, sub_index, size):
    """Read from a CANopen object"""
    try:
        # Format according to manual
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
            (index >> 8) & 0xFF, index & 0xFF,  # Object Index
            sub_index,   # Sub Index
            0x00, 0x00,  # Starting Address
            0x00,        # SDO Object
            size         # Byte count
        ])
        
        print(f"Reading object 0x{index:04X}:{sub_index}")
        print_packet(packet, True)
        sock.send(packet)
        
        response = sock.recv(1024)
        print_packet(response, False)
        
        # Check for response
        if len(response) >= 19 + size:
            value = 0
            for i in range(size):
                value |= response[19 + i] << (8 * i)
            
            print(f"Object 0x{index:04X}:{sub_index} value: {value} (0x{value:X})")
            return value
        else:
            print(f"Response too short when reading object 0x{index:04X}:{sub_index}")
            return None
            
    except Exception as e:
        print(f"Error reading object: {e}")
        return None

def go_through_state_machine(sock, name="Controller"):
    """Go through the state machine to reach 'Operation Enabled' state"""
    # First check current status
    print(f"\n=== Starting state machine sequence for {name} ===")
    
    print("\nReading initial statusword...")
    status = read_statusword(sock)
    if status is None:
        print("Failed to read statusword - aborting state machine")
        return False
    
    # Check if DI7 (Enable) is set
    if not (status & 0x0200):
        print("\n!!! WARNING: DI7 (Enable) is not set high. Motors cannot be powered !!!")
        print("Please check hardware connection for Digital Input 7")
        print("Continuing with state machine, but motor will not move without DI7 set")
    
    # Check current state and decide next step
    state = STATE_UNKNOWN
    if (status & 0x004F) == 0x0000:
        state = STATE_NOT_READY
    elif (status & 0x004F) == 0x0040:
        state = STATE_SWITCH_ON_DISABLED
    elif (status & 0x006F) == 0x0021:
        state = STATE_READY_TO_SWITCH_ON
    elif (status & 0x006F) == 0x0023:
        state = STATE_SWITCHED_ON
    elif (status & 0x006F) == 0x0027:
        state = STATE_OPERATION_ENABLED
    elif (status & 0x004F) == 0x0008:
        state = STATE_FAULT
    
    print(f"Current state: {STATE_NAMES.get(state, 'Unknown')}")
    
    # Handle potential fault state
    if state == STATE_FAULT:
        print("\nController is in FAULT state. Attempting fault reset...")
        write_controlword(sock, 0x0080)  # Fault reset
        time.sleep(1)
        status = read_statusword(sock)
        
        # Re-check state after fault reset
        if (status & 0x004F) == 0x0040:
            state = STATE_SWITCH_ON_DISABLED
            print("Fault cleared, now in Switch On Disabled state")
        else:
            print("Failed to clear fault - please check controller")
            return False
    
    # If Not Ready, wait for state to change
    if state == STATE_NOT_READY:
        print("\nController is in NOT READY state. Waiting for it to become ready...")
        for _ in range(5):
            time.sleep(1)
            status = read_statusword(sock)
            if (status & 0x004F) == 0x0040:  # Switch On Disabled
                state = STATE_SWITCH_ON_DISABLED
                print("Controller is now in Switch On Disabled state")
                break
        
        if state == STATE_NOT_READY:
            print("Controller didn't become ready in time - please check configuration")
            return False
    
    # From Switch On Disabled to Ready To Switch On
    if state == STATE_SWITCH_ON_DISABLED:
        print("\nSending 'Shutdown' command...")
        write_controlword(sock, 0x0006)  # Shutdown (disable voltage + quick stop)
        time.sleep(1)
        status = read_statusword(sock)
        
        if (status & 0x006F) == 0x0021:
            state = STATE_READY_TO_SWITCH_ON
            print("Successfully reached 'Ready to Switch On' state")
        else:
            print("Failed to reach 'Ready to Switch On' state")
            return False
    
    # From Ready To Switch On to Switched On
    if state == STATE_READY_TO_SWITCH_ON:
        print("\nSending 'Switch On' command...")
        write_controlword(sock, 0x0007)  # Switch On
        time.sleep(1)
        status = read_statusword(sock)
        
        if (status & 0x006F) == 0x0023:
            state = STATE_SWITCHED_ON
            print("Successfully reached 'Switched On' state")
        else:
            print("Failed to reach 'Switched On' state")
            return False
    
    # From Switched On to Operation Enabled
    if state == STATE_SWITCHED_ON:
        print("\nSending 'Enable Operation' command...")
        write_controlword(sock, 0x000F)  # Enable Operation
        time.sleep(1)
        status = read_statusword(sock)
        
        if (status & 0x006F) == 0x0027:
            state = STATE_OPERATION_ENABLED
            print("Successfully reached 'Operation Enabled' state")
        else:
            print("Failed to reach 'Operation Enabled' state")
            return False
    
    if state == STATE_OPERATION_ENABLED:
        print("\nController is now in 'Operation Enabled' state and ready for commands")
        return True
    else:
        print(f"\nFailed to reach 'Operation Enabled' state, stopped in {STATE_NAMES.get(state, 'Unknown')}")
        return False

def test_simple_movement(sock, name="Controller"):
    """Test a simple movement in Profile Position mode with detailed feedback"""
    print(f"\n=== Starting test movement for {name} ===")
    
    # Read current position before starting
    print("\nReading current position...")
    current_pos = read_object(sock, 0x6064, 0, 4)  # Position Actual Value
    if current_pos is None:
        print("Failed to read current position")
        return False
    
    # Read mode of operation display
    print("\nChecking current operation mode...")
    op_mode = read_object(sock, 0x6061, 0, 1)  # Modes of Operation Display
    if op_mode is None:
        print("Failed to read operation mode")
        return False
    
    # Set operation mode to Profile Position (1)
    if op_mode != 1:
        print("\nSetting operation mode to Profile Position...")
        if not write_object(sock, 0x6060, 0, 1, 1):
            print("Failed to set operation mode")
            return False
            
        # Verify operation mode change
        time.sleep(0.5)
        op_mode = read_object(sock, 0x6061, 0, 1)
        if op_mode != 1:
            print(f"Operation mode didn't change to Profile Position (current mode: {op_mode})")
            return False
    else:
        print("Operation mode is already Profile Position")
    
    # Check if controller is enabled
    print("\nVerifying controller state...")
    status = read_statusword(sock)
    if status is None or (status & 0x006F) != 0x0027:
        print("Controller is not in Operation Enabled state")
        return False
    
    # Set some key parameters
    print("\nReading feed constant...")
    feed_constant = read_object(sock, 0x6092, 1, 4)  # Feed constant (feed)
    if feed_constant is None:
        print("Failed to read feed constant, using default value of 1000")
        feed_constant = 1000
    else:
        print(f"Feed constant: {feed_constant}")
    
    # Set target position (1000 increments)
    target_position = 1000
    print(f"\nSetting target position to {target_position}...")
    if not write_object(sock, 0x607A, 0, target_position, 4):
        print("Failed to set target position")
        return False
    
    # Set profile velocity
    velocity = 1000
    print(f"\nSetting profile velocity to {velocity}...")
    if not write_object(sock, 0x6081, 0, velocity, 4):
        print("Failed to set profile velocity")
        return False
    
    # Set profile acceleration
    acceleration = 2000
    print(f"\nSetting profile acceleration to {acceleration}...")
    if not write_object(sock, 0x6083, 0, acceleration, 4):
        print("Failed to set profile acceleration")
        return False
    
    # Start the movement (bit 4 set to 1)
    print("\nStarting movement...")
    if not write_controlword(sock, 0x001F):
        print("Failed to start movement")
        return False
    
    # Wait for movement to complete
    print("\nWaiting for movement to complete...")
    movement_completed = False
    for i in range(20):  # Longer timeout
        print(f"Checking status, attempt {i+1}/20...")
        status = read_statusword(sock)
        
        if status is None:
            print("Failed to read status")
            time.sleep(1)
            continue
            
        # Check target reached bit
        if status & 0x0400:
            print("Movement completed successfully!")
            movement_completed = True
            break
            
        # Check if controller is still enabled
        if (status & 0x006F) != 0x0027:
            print("Controller left Operation Enabled state during movement")
            break
            
        # Read current position for progress tracking
        current_pos = read_object(sock, 0x6064, 0, 4)
        if current_pos is not None:
            print(f"Current position: {current_pos}")
            
        time.sleep(1)
    
    if not movement_completed:
        print("Movement did not complete in the expected time")
        
    # Reset the start bit
    print("\nResetting start bit...")
    write_controlword(sock, 0x000F)
    
    # Return to start position
    print("\nSetting target position to 0...")
    if not write_object(sock, 0x607A, 0, 0, 4):
        print("Failed to set return position")
        return False
    
    # Start the movement
    print("\nReturning to start position...")
    if not write_controlword(sock, 0x001F):
        print("Failed to start return movement")
        return False
    
    # Wait for movement to complete
    print("\nWaiting for return movement to complete...")
    return_completed = False
    for i in range(20):  # Longer timeout
        print(f"Checking status, attempt {i+1}/20...")
        status = read_statusword(sock)
        
        if status is None:
            print("Failed to read status")
            time.sleep(1)
            continue
            
        # Check target reached bit
        if status & 0x0400:
            print("Return movement completed successfully!")
            return_completed = True
            break
            
        # Check if controller is still enabled
        if (status & 0x006F) != 0x0027:
            print("Controller left Operation Enabled state during return movement")
            break
            
        # Read current position for progress tracking
        current_pos = read_object(sock, 0x6064, 0, 4)
        if current_pos is not None:
            print(f"Current position: {current_pos}")
            
        time.sleep(1)
    
    if not return_completed:
        print("Return movement did not complete in the expected time")
    
    # Reset the start bit
    print("\nResetting start bit...")
    write_controlword(sock, 0x000F)
    
    return movement_completed and return_completed

def check_modbus_gateway_setting(sock):
    """Check if Modbus TCP Gateway is properly configured"""
    print("\n=== Checking Controller Configuration ===")
    
    # Check CANopen settings
    try:
        print("\nChecking if any bus system is active...")
        # Reading device type (object 1000h) - this should work if Modbus is properly configured
        device_type = read_object(sock, 0x1000, 0, 4)
        if device_type is None:
            print("Unable to read device information - Modbus gateway might not be properly configured")
            return False
        else:
            print(f"Device type: 0x{device_type:08X}")
        
        # Try to check statusword - this will also tell us if a drive mode is set as dominant
        print("\nChecking statusword to verify communication...")
        status = read_statusword(sock)
        if status is None:
            print("Unable to read statusword - Modbus gateway might not be properly configured")
            return False
        
        # Try reading operation mode to detect drive mode selection
        print("\nChecking operation mode...")
        op_mode_display = read_object(sock, 0x6061, 0, 1)
        if op_mode_display is None:
            print("Unable to read operation mode - communication issue")
            return False
            
        print(f"Current operation mode: {op_mode_display}")
        
        # Check if we can read motor current - indicates motor configuration
        print("\nChecking motor current setting...")
        motor_current = read_object(sock, 0x2000, 1, 2)  # Motor Current Actual Value
        if motor_current is None:
            print("Unable to read motor current - communication issue")
        else:
            print(f"Motor current: {motor_current} mA")
        
        print("\nModbus TCP Gateway appears to be properly configured.")
        return True
        
    except Exception as e:
        print(f"Error checking Modbus configuration: {e}")
        return False

def main():
    while True:
        print("\n========== Motor Controller Test Menu ==========")
        print("1) Check Y-axis controller configuration")
        print("2) Check Z-axis controller configuration")
        print("3) Test Y-axis controller")
        print("4) Test Z-axis controller")
        print("5) Test both controllers sequentially")
        print("6) Exit")
        
        choice = input("Enter your choice (1-6): ")
        
        if choice == '1':
            y_sock = create_connection(Y_CONTROLLER_IP)
            if y_sock:
                try:
                    print("\n--- Checking Y-axis controller configuration ---")
                    check_modbus_gateway_setting(y_sock)
                finally:
                    y_sock.close()
                    
        elif choice == '2':
            z_sock = create_connection(Z_CONTROLLER_IP)
            if z_sock:
                try:
                    print("\n--- Checking Z-axis controller configuration ---")
                    check_modbus_gateway_setting(z_sock)
                finally:
                    z_sock.close()
                    
        elif choice == '3':
            y_sock = create_connection(Y_CONTROLLER_IP)
            if y_sock:
                try:
                    print("\n--- Testing Y-axis controller ---")
                    if go_through_state_machine(y_sock, "Y-axis"):
                        test_simple_movement(y_sock, "Y-axis")
                finally:
                    y_sock.close()
                    
        elif choice == '4':
            z_sock = create_connection(Z_CONTROLLER_IP)
            if z_sock:
                try:
                    print("\n--- Testing Z-axis controller ---")
                    if go_through_state_machine(z_sock, "Z-axis"):
                        test_simple_movement(z_sock, "Z-axis")
                finally:
                    z_sock.close()
                    
        elif choice == '5':
            y_sock = create_connection(Y_CONTROLLER_IP)
            z_sock = create_connection(Z_CONTROLLER_IP)
            
            if y_sock and z_sock:
                try:
                    print("\n--- Testing Y-axis controller ---")
                    if go_through_state_machine(y_sock, "Y-axis"):
                        test_simple_movement(y_sock, "Y-axis")
                    
                    print("\n--- Testing Z-axis controller ---")
                    if go_through_state_machine(z_sock, "Z-axis"):
                        test_simple_movement(z_sock, "Z-axis")
                finally:
                    if y_sock:
                        y_sock.close()
                    if z_sock:
                        z_sock.close()
                    
        elif choice == '6':
            print("Exiting...")
            sys.exit(0)
            
        else:
            print("Invalid choice. Please enter a number between 1 and 6.")

if __name__ == "__main__":
    main()