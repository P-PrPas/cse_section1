import cv2
from PySide6.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QLabel, QComboBox, QLineEdit, QPushButton
from PySide6.QtMultimedia import QMediaDevices

from utils.config import save_config

class SettingsDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("⚙️ System Configuration")
        self.setMinimumWidth(450)
        if parent:
            self.config = parent.config.copy()
        else:
            self.config = {}

        layout = QVBoxLayout(self)
        layout.setSpacing(15)
        layout.setContentsMargins(24, 24, 24, 24)
        
        title = QLabel("<b>Hardware & System Settings</b>")
        title.setStyleSheet("font-size: 18px;")
        layout.addWidget(title)

        # Camera Selection
        cam_layout = QHBoxLayout()
        cam_layout.addWidget(QLabel("Video Input Device:"))
        self.cam_combo = QComboBox()
        self.populate_cameras()
        cam_layout.addWidget(self.cam_combo)
        layout.addLayout(cam_layout)

        # Output Directory
        out_layout = QHBoxLayout()
        out_layout.addWidget(QLabel("Evidence Output Directory:"))
        self.out_input = QLineEdit(self.config.get("output_dir", "./output"))
        out_layout.addWidget(self.out_input)
        layout.addLayout(out_layout)

        # Timeout
        timeout_layout = QHBoxLayout()
        timeout_layout.addWidget(QLabel("Network Timeout (Seconds):"))
        self.timeout_input = QLineEdit(str(self.config.get("scraper_timeout_sec", 15)))
        timeout_layout.addWidget(self.timeout_input)
        layout.addLayout(timeout_layout)
        
        layout.addSpacing(20)

        # Buttons
        btn_layout = QHBoxLayout()
        save_btn = QPushButton("✅ Save Configuration")
        save_btn.clicked.connect(self.save_and_close)
        
        cancel_btn = QPushButton("❌ Cancel")
        cancel_btn.setObjectName("SecondaryBtn")
        cancel_btn.clicked.connect(self.reject)
        
        btn_layout.addWidget(cancel_btn)
        btn_layout.addWidget(save_btn)
        layout.addLayout(btn_layout)

    def populate_cameras(self):
        cameras = QMediaDevices.videoInputs()
        current_cam_idx = self.config.get("camera_index", 0)
        
        if not cameras:
            self.cam_combo.addItem("No Camera Found", 0)
            return

        for idx, cam in enumerate(cameras):
            self.cam_combo.addItem(f"{cam.description()}", idx)
            if idx == current_cam_idx:
                self.cam_combo.setCurrentIndex(idx)

    def save_and_close(self):
        try:
            timeout = int(self.timeout_input.text())
        except:
            timeout = 15
            
        self.config["camera_index"] = self.cam_combo.currentData()
        self.config["output_dir"] = self.out_input.text()
        self.config["scraper_timeout_sec"] = timeout
        
        save_config(self.config)
        self.accept()
