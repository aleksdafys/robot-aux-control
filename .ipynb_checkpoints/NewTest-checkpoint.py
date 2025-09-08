import sys
from PyQt5.QtWidgets import QApplication, QMainWindow, QPushButton, QCheckBox, QGridLayout, QWidget, QLabel, QVBoxLayout, QHBoxLayout
from PyQt5.QtCore import QTimer, pyqtSignal, Qt
from PyQt5.QtGui import QFont, QPalette, QColor
import time

class RobotAuxiliaryUI(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Robot Auxiliary Systems Control")
        self.setGeometry(100, 100, 800, 600)
        
        # State variables for 8 auxiliaries
        self.aux_states = {i: False for i in range(1, 9)}
        self.disco_mode_active = False
        
        # Timer for disco mode continuous rotation
        self.disco_timer = QTimer()
        self.disco_timer.timeout.connect(self.disco_step)
        self.disco_step_delay = 100  # milliseconds between steps
        
        # Hardware configuration - map auxiliary numbers to hardware functions
        self.aux_config = {
            1: {"name": "Air Supply", "function": self.control_air_supply},
            2: {"name": "Vacuum", "function": self.control_vacuum},
            3: {"name": "Laser", "function": self.control_laser},
            4: {"name": "Coolant", "function": self.control_coolant},
            5: {"name": "Spindle", "function": self.control_spindle},
            6: {"name": "Dust Collection", "function": self.control_dust_collection},
            7: {"name": "Work Light", "function": self.control_work_light},
            8: {"name": "Probe", "function": self.control_probe}
        }
        
        self.setup_ui()
        
    def setup_ui(self):
        """Create the main UI layout"""
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # Main layout
        main_layout = QVBoxLayout(central_widget)
        
        # Title
        title_label = QLabel("AUX CONTROL SYSTEM")
        title_font = QFont()
        title_font.setPointSize(18)
        title_font.setBold(True)
        title_label.setFont(title_font)
        title_label.setAlignment(Qt.AlignCenter)
        title_label.setStyleSheet("color: #2c3e50; margin: 10px;")
        main_layout.addWidget(title_label)
        
        # Create 2x4 grid of auxiliary toggle buttons
        self.create_aux_grid(main_layout)
        
        # Manual control section
        self.create_manual_controls(main_layout)
        
        # Status display
        self.create_status_display(main_layout)
        
        # Emergency stop
        self.create_emergency_controls(main_layout)
        
        # Apply styling
        self.apply_styling()
    
    def create_aux_grid(self, parent_layout):
        """Create 2x4 grid of auxiliary toggle buttons"""
        aux_widget = QWidget()
        aux_layout = QGridLayout(aux_widget)
        aux_layout.setSpacing(15)
        
        # Grid label
        grid_label = QLabel("Auxiliary Systems")
        grid_label.setAlignment(Qt.AlignCenter)
        grid_label.setStyleSheet("font-weight: bold; font-size: 14px; color: #34495e; margin-bottom: 10px;")
        parent_layout.addWidget(grid_label)
        
        # Create 2x4 grid (2 rows, 4 columns)
        self.aux_buttons = {}
        for i in range(1, 9):
            row = (i - 1) // 4  # 0 for buttons 1-4, 1 for buttons 5-8
            col = (i - 1) % 4   # 0-3 for each row
            
            button = QPushButton(f"AUX {i}\n{self.aux_config[i]['name']}")
            button.setCheckable(True)  # Makes it a toggle button
            button.setMinimumSize(150, 80)
            button.clicked.connect(lambda checked, aux_num=i: self.toggle_auxiliary(aux_num, checked))
            
            self.aux_buttons[i] = button
            aux_layout.addWidget(button, row, col)
        
        parent_layout.addWidget(aux_widget)
    
    def create_manual_controls(self, parent_layout):
        """Create manual control section"""
        manual_widget = QWidget()
        manual_layout = QHBoxLayout(manual_widget)
        
        # Manual rotation controls
        rotation_label = QLabel("Laser Mirror Control:")
        rotation_label.setStyleSheet("font-weight: bold; margin-right: 10px;")
        manual_layout.addWidget(rotation_label)
        
        self.minus_5_button = QPushButton("-5°")
        self.minus_5_button.setMinimumSize(60, 40)
        self.minus_5_button.clicked.connect(self.rotate_minus_5)
        manual_layout.addWidget(self.minus_5_button)
        
        self.plus_5_button = QPushButton("+5°")
        self.plus_5_button.setMinimumSize(60, 40)
        self.plus_5_button.clicked.connect(self.rotate_plus_5)
        manual_layout.addWidget(self.plus_5_button)
        
        # Disco mode
        manual_layout.addWidget(QLabel("  |  "))
        
        self.disco_button = QPushButton("🕺 DISCO MODE")
        self.disco_button.setCheckable(True)
        self.disco_button.setMinimumSize(120, 40)
        self.disco_button.clicked.connect(self.toggle_disco_mode)
        manual_layout.addWidget(self.disco_button)
        
        manual_layout.addStretch()  # Push everything to the left
        parent_layout.addWidget(manual_widget)
    
    def create_status_display(self, parent_layout):
        """Create status display area"""
        self.status_label = QLabel("System Status: All systems off")
        self.status_label.setAlignment(Qt.AlignCenter)
        self.status_label.setMinimumHeight(60)
        self.status_label.setStyleSheet("""
            background-color: #ecf0f1; 
            border: 2px solid #bdc3c7; 
            border-radius: 5px; 
            font-size: 14px; 
            padding: 10px;
            margin: 10px 0px;
        """)
        parent_layout.addWidget(self.status_label)
    
    def create_emergency_controls(self, parent_layout):
        """Create emergency stop button"""
        emergency_widget = QWidget()
        emergency_layout = QHBoxLayout(emergency_widget)
        
        emergency_layout.addStretch()
        
        self.emergency_button = QPushButton("🚨 EMERGENCY STOP 🚨")
        self.emergency_button.setMinimumSize(200, 50)
        self.emergency_button.clicked.connect(self.emergency_stop)
        self.emergency_button.setStyleSheet("""
            QPushButton {
                background-color: #e74c3c; 
                color: white; 
                font-weight: bold; 
                font-size: 16px;
                border: none;
                border-radius: 10px;
            }
            QPushButton:hover {
                background-color: #c0392b;
            }
            QPushButton:pressed {
                background-color: #a93226;
            }
        """)
        
        emergency_layout.addWidget(self.emergency_button)
        emergency_layout.addStretch()
        
        parent_layout.addWidget(emergency_widget)
    
    def apply_styling(self):
        """Apply consistent styling to the UI"""
        # Style for auxiliary buttons
        aux_button_style = """
            QPushButton {
                background-color: #95a5a6;
                color: white;
                border: 2px solid #7f8c8d;
                border-radius: 8px;
                font-weight: bold;
                font-size: 12px;
            }
            QPushButton:checked {
                background-color: #27ae60;
                border: 2px solid #229954;
            }
            QPushButton:hover {
                background-color: #85929e;
            }
            QPushButton:checked:hover {
                background-color: #239b56;
            }
        """
        
        for button in self.aux_buttons.values():
            button.setStyleSheet(aux_button_style)
        
        # Style for manual control buttons
        manual_button_style = """
            QPushButton {
                background-color: #3498db;
                color: white;
                border: none;
                border-radius: 5px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #2980b9;
            }
            QPushButton:pressed {
                background-color: #21618c;
            }
        """
        
        self.plus_5_button.setStyleSheet(manual_button_style)
        self.minus_5_button.setStyleSheet(manual_button_style)
        
        # Disco button special styling
        disco_style = """
            QPushButton {
                background-color: #9b59b6;
                color: white;
                border: none;
                border-radius: 5px;
                font-weight: bold;
            }
            QPushButton:checked {
                background-color: #e91e63;
                animation: blink 1s infinite;
            }
            QPushButton:hover {
                background-color: #8e44ad;
            }
        """
        self.disco_button.setStyleSheet(disco_style)
    
    def toggle_auxiliary(self, aux_num, checked):
        """Toggle auxiliary system on/off"""
        self.aux_states[aux_num] = checked
        aux_name = self.aux_config[aux_num]["name"]
        
        if checked:
            print(f"✅ AUX {aux_num} ({aux_name}): ACTIVATED")
        else:
            print(f"❌ AUX {aux_num} ({aux_name}): DEACTIVATED")
        
        # Call the specific hardware control function
        self.aux_config[aux_num]["function"](checked)
        
        # Update status display
        self.update_status_display()
    
    def rotate_plus_5(self):
        """Rotate laser mirror +5 degrees"""
        if self.disco_mode_active:
            print("Cannot manual rotate - Disco Mode is active!")
            return
        
        print("Rotating laser mirror +5 degrees")
        self.rotate_stepper(5)
    
    def rotate_minus_5(self):
        """Rotate laser mirror -5 degrees"""
        if self.disco_mode_active:
            print("Cannot manual rotate - Disco Mode is active!")
            return
        
        print("Rotating laser mirror -5 degrees")
        self.rotate_stepper(-5)
    
    def toggle_disco_mode(self, checked):
        """Toggle disco mode - continuous stepper rotation"""
        self.disco_mode_active = checked
        if checked:
            print("🕺 DISCO MODE: ACTIVATED 🕺")
            self.disco_timer.start(self.disco_step_delay)
            # Disable manual rotation buttons
            self.plus_5_button.setEnabled(False)
            self.minus_5_button.setEnabled(False)
            self.disco_button.setText("🕺 DISCO ON 🕺")
        else:
            print("Disco Mode: DEACTIVATED")
            self.disco_timer.stop()
            # Re-enable manual rotation buttons
            self.plus_5_button.setEnabled(True)
            self.minus_5_button.setEnabled(True)
            self.disco_button.setText("🕺 DISCO MODE")
        
        self.update_status_display()
    
    def disco_step(self):
        """Perform one step of disco mode rotation"""
        # Small step for continuous rotation
        self.rotate_stepper(1)  # 1 degree steps for smooth motion
    
    # Hardware control functions for each auxiliary
    def control_air_supply(self, state):
        """Control air supply system"""
        if state:
            print("  🌬️  Activating air supply...")
            # Your hardware control code here
        else:
            print("  🌬️  Deactivating air supply...")
    
    def control_vacuum(self, state):
        """Control vacuum/dust collection"""
        if state:
            print("  💨 Activating vacuum system...")
        else:
            print("  💨 Deactivating vacuum system...")
    
    def control_laser(self, state):
        """Control laser system"""
        if state:
            print("  🔴 Activating laser - SAFETY PROTOCOLS ACTIVE...")
        else:
            print("  🔴 Deactivating laser...")
    
    def control_coolant(self, state):
        """Control coolant system"""
        if state:
            print("  💧 Activating coolant flow...")
        else:
            print("  💧 Stopping coolant flow...")
    
    def control_spindle(self, state):
        """Control spindle motor"""
        if state:
            print("  ⚙️  Starting spindle motor...")
        else:
            print("  ⚙️  Stopping spindle motor...")
    
    def control_dust_collection(self, state):
        """Control dust collection system"""
        if state:
            print("  🌪️  Activating dust collection...")
        else:
            print("  🌪️  Deactivating dust collection...")
    
    def control_work_light(self, state):
        """Control work area lighting"""
        if state:
            print("  💡 Turning on work lights...")
        else:
            print("  💡 Turning off work lights...")
    
    def control_probe(self, state):
        """Control probe system"""
        if state:
            print("  📏 Activating probe system...")
        else:
            print("  📏 Deactivating probe system...")
    
    def rotate_stepper(self, degrees):
        """Send command to rotate stepper motor by specified degrees"""
        # Replace with your actual stepper motor control
        print(f"  🔄 Rotating stepper {degrees}°")
        # Example: self.stepper_controller.rotate(degrees)
        pass
    
    def update_status_display(self):
        """Update the status display on the UI"""
        active_systems = []
        
        # Check auxiliary systems
        for aux_num, state in self.aux_states.items():
            if state:
                aux_name = self.aux_config[aux_num]["name"]
                active_systems.append(f"AUX{aux_num}({aux_name})")
        
        # Check disco mode
        if self.disco_mode_active:
            active_systems.append("🕺DISCO🕺")
        
        if active_systems:
            status_text = f"ACTIVE: {' | '.join(active_systems)}"
            self.status_label.setStyleSheet("""
                background-color: #d5f4e6; 
                border: 2px solid #27ae60; 
                border-radius: 5px; 
                font-size: 14px; 
                padding: 10px;
                margin: 10px 0px;
                color: #1e8449;
            """)
        else:
            status_text = "System Status: All systems off"
            self.status_label.setStyleSheet("""
                background-color: #ecf0f1; 
                border: 2px solid #bdc3c7; 
                border-radius: 5px; 
                font-size: 14px; 
                padding: 10px;
                margin: 10px 0px;
                color: #2c3e50;
            """)
        
        self.status_label.setText(status_text)
    
    def emergency_stop(self):
        """Emergency stop all systems"""
        print("🚨 EMERGENCY STOP ACTIVATED 🚨")
        
        # Turn off all auxiliary systems
        for aux_num in range(1, 9):
            if self.aux_states[aux_num]:
                self.aux_buttons[aux_num].setChecked(False)
                self.toggle_auxiliary(aux_num, False)
        
        # Update display
        self.status_label.setText("🚨 EMERGENCY STOP - ALL SYSTEMS DISABLED 🚨")
        self.status_label.setStyleSheet("""
            background-color: #fadbd8; 
            border: 2px solid #e74c3c; 
            border-radius: 5px; 
            font-size: 14px; 
            padding: 10px;
            margin: 10px 0px;
            color: #c0392b;
            font-weight: bold;
        """)
        
        print("All auxiliary systems have been shut down safely.")
    
    def closeEvent(self, event):
        """Clean shutdown when window is closed"""
        print("Shutting down auxiliary systems...")
        self.emergency_stop()
        event.accept()


if __name__ == '__main__':
    app = QApplication(sys.argv)
    
    # Create and show the main window
    window = RobotAuxiliaryUI()
    window.show()
    
    # Start the application
    sys.exit(app.exec_())