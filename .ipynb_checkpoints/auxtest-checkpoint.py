import sys
from PyQt5.QtWidgets import QApplication, QMainWindow, QPushButton, QCheckBox
from PyQt5.QtCore import QTimer, pyqtSignal
from aux_test_ui import Ui_MainWindow  # Your exported UI file
import time
import libioplus

class RobotAuxiliaryUI(QMainWindow):
    def __init__(self):
        super().__init__()
        self.ui = Ui_MainWindow()
        self.ui.setupUi(self)
        
        # State variables
        self.air_in_active = False
        self.air_out_active = False
        self.laser_on_active = False
        self.disco_mode_active = False
        
        # Timer for disco mode continuous rotation
        self.disco_timer = QTimer()
        self.disco_timer.timeout.connect(self.disco_step)
        self.disco_step_delay = 100  # milliseconds between steps
        
        # Connect UI elements to functions
        # Assuming your object names from Qt Designer are:
        self.connect_signals()
        
    def connect_signals(self):
        """Connect all UI elements to their respective functions"""
        # Toggle buttons (assuming they are checkboxes or toggle buttons)
        # Replace these with your actual object names from Qt Designer
        try:
            # Air system controls
            self.ui.air_in_button.toggled.connect(self.toggle_air_in)
            self.ui.air_out_button.toggled.connect(self.toggle_air_out)
            
            # Laser control
            self.ui.laser_button.toggled.connect(self.toggle_laser)
            
            # Stepper motor controls
            self.ui.plus_5_deg_button.clicked.connect(self.rotate_plus_5)
            self.ui.minus_5_deg_button.clicked.connect(self.rotate_minus_5)
            
            # Disco mode
            self.ui.disco_button.toggled.connect(self.toggle_disco_mode)
            
        except AttributeError as e:
            print(f"UI element not found: {e}")
            print("Make sure to update object names to match your Qt Designer names")
    
    def toggle_air_in(self, checked):
        """Toggle air supply to toolhead"""
        self.air_in_active = checked
        if checked:
            print("Air In: ACTIVATED")
            self.activate_air_supply()
        else:
            print("Air In: DEACTIVATED")
            self.deactivate_air_supply()
        
        # Update UI feedback
        self.update_status_display()
    
    def toggle_air_out(self, checked):
        """Toggle vacuum/dust collection"""
        self.air_out_active = checked
        if checked:
            print("Air Out (Vacuum): ACTIVATED")
            self.activate_vacuum()
        else:
            print("Air Out (Vacuum): DEACTIVATED")
            self.deactivate_vacuum()
        
        self.update_status_display()
    
    def toggle_laser(self, checked):
        """Toggle laser cleaner"""
        self.laser_on_active = checked
        if checked:
            print("Laser: ON")
            self.activate_laser()
        else:
            print("Laser: OFF")
            self.deactivate_laser()
        
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
            self.ui.plus_5_deg_button.setEnabled(False)
            self.ui.minus_5_deg_button.setEnabled(False)
        else:
            print("Disco Mode: DEACTIVATED")
            self.disco_timer.stop()
            # Re-enable manual rotation buttons
            self.ui.plus_5_deg_button.setEnabled(True)
            self.ui.minus_5_deg_button.setEnabled(True)
        
        self.update_status_display()
    
    def disco_step(self):
        """Perform one step of disco mode rotation"""
        # Small step for continuous rotation
        self.rotate_stepper(1)  # 1 degree steps for smooth motion
    
    # Hardware interface functions - replace with your actual hardware control
    def activate_air_supply(self):
        """Send command to activate air supply"""
        setRelayCh(0,1,1)
        pass
    
    def deactivate_air_supply(self):
        """Send command to deactivate air supply"""
        setRelayCh(0,1,0)
        pass
    
    def activate_vacuum(self):
        """Send command to activate vacuum/dust collection"""
        setRelayCh(0,2,1)
        pass
    
    def deactivate_vacuum(self):
        """Send command to deactivate vacuum"""
        setRelayCh(0,2,1)
        pass
    
    def activate_laser(self):
        """Send command to turn on laser cleaner"""
        setRelayCh(0,3,1)
        pass
    
    def deactivate_laser(self):
        """Send command to turn off laser cleaner"""
        setRelayCh(0,3,0)
        pass
    
    def rotate_stepper(self, degrees):
        """Send command to rotate stepper motor by specified degrees"""
        # Replace with your actual stepper motor control
        # Example: self.stepper_controller.rotate(degrees)
        pass
    
    def update_status_display(self):
        """Update the status display on the UI"""
        status_parts = []
        
        if self.air_in_active:
            status_parts.append("AIR-IN")
        if self.air_out_active:
            status_parts.append("VACUUM")
        if self.laser_on_active:
            status_parts.append("LASER")
        if self.disco_mode_active:
            status_parts.append("🕺DISCO🕺")
        
        status_text = " | ".join(status_parts) if status_parts else "All systems off"
        
        # Update status label (replace with your actual status label object name)
        try:
            self.ui.status_label.setText(status_text)
        except AttributeError:
            print(f"Status: {status_text}")
    
    def emergency_stop(self):
        """Emergency stop all systems"""
        print("🚨 EMERGENCY STOP 🚨")
        
        # Turn off all systems
        if hasattr(self.ui, 'air_in_button'):
            self.ui.air_in_button.setChecked(False)
        if hasattr(self.ui, 'air_out_button'):
            self.ui.air_out_button.setChecked(False)
        if hasattr(self.ui, 'laser_button'):
            self.ui.laser_button.setChecked(False)
        if hasattr(self.ui, 'disco_button'):
            self.ui.disco_button.setChecked(False)
        
        # Stop all hardware
        self.deactivate_air_supply()
        self.deactivate_vacuum()
        self.deactivate_laser()
        self.disco_timer.stop()
        
        self.update_status_display()
    
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