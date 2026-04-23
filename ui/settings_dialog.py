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
        refresh_btn = QPushButton("Refresh")
        refresh_btn.setObjectName("SecondaryBtn")
        refresh_btn.clicked.connect(self.refresh_cameras)
        cam_layout.addWidget(refresh_btn)
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
        self.cam_combo.clear()
        cameras = QMediaDevices.videoInputs()
        current_cam_idx = self.config.get("camera_index", 0)
        current_cam_name = self.config.get("camera_name", "")
        
        if not cameras:
            self.cam_combo.addItem("No Camera Found", {"index": 0, "name": "No Camera Found"})
            return

        for idx, cam in enumerate(cameras):
            label = cam.description() or f"Camera {idx}"
            self.cam_combo.addItem(label, {"index": idx, "name": label})

            if current_cam_name and label == current_cam_name:
                self.cam_combo.setCurrentIndex(self.cam_combo.count() - 1)
            elif not current_cam_name and idx == current_cam_idx:
                self.cam_combo.setCurrentIndex(self.cam_combo.count() - 1)

    def refresh_cameras(self):
        self.populate_cameras()

    def save_and_close(self):
        try:
            timeout = int(self.timeout_input.text())
        except:
            timeout = 15

        camera_data = self.cam_combo.currentData() or {"index": 0, "name": "Default"}
        self.config["camera_index"] = int(camera_data.get("index", 0))
        self.config["camera_name"] = camera_data.get("name", "")
        self.config["output_dir"] = self.out_input.text()
        self.config["scraper_timeout_sec"] = timeout
        
        save_config(self.config)
        self.accept()
