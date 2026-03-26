import cv2
import numpy as np
from PySide6.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton, QScrollArea, QWidget, QMessageBox
from PySide6.QtCore import Qt
from PySide6.QtGui import QImage, QPixmap

class OverrideModal(QDialog):
    def __init__(self, doc_image: np.ndarray, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Manual Data Entry | Security Override")
        self.setMinimumSize(1200, 800) # Increased to 80% screen width as requested
        self.exam_id = None
        
        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(20)
        
        # --- LEFT PANE : Huge Document Viewer ---
        left_pane = QWidget()
        left_layout = QVBoxLayout(left_pane)
        left_layout.setContentsMargins(0, 0, 0, 0)
        
        title_left = QLabel("<b>📄 Captured Document Preview</b>")
        left_layout.addWidget(title_left)

        # Allow the image to be scrolled and panned if it is taller than the window
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        # Added significant dark padding so the white paper doesn't bleed into the edges
        self.scroll_area.setStyleSheet("background-color: #0b1120; border-radius: 8px; border: 1px solid #1e293b; padding: 24px;")
        
        self.img_label = QLabel("Loading preview...")
        self.img_label.setAlignment(Qt.AlignCenter)
        self.scroll_area.setWidget(self.img_label)
        
        left_layout.addWidget(self.scroll_area)
        main_layout.addWidget(left_pane, stretch=7) # 70% of modal width
        
        # --- RIGHT PANE : Data Entry ---
        right_pane = QWidget()
        right_pane.setObjectName("Card")
        right_layout = QVBoxLayout(right_pane)
        right_layout.setContentsMargins(24, 24, 24, 24)
        
        title_right = QLabel("<b>✏️ Applicant Exam ID</b>")
        title_right.setAlignment(Qt.AlignCenter)
        title_right.setStyleSheet("font-size: 18px;")
        right_layout.addWidget(title_right)
        
        right_layout.addSpacing(20)
        
        instruction = QLabel("Please verify the document on the left and\ninput the 9-digit Exam ID below:")
        instruction.setStyleSheet("color: #cbd5e1; line-height: 1.5;")
        instruction.setAlignment(Qt.AlignCenter)
        right_layout.addWidget(instruction)
        
        self.input_field = QLineEdit()
        self.input_field.setPlaceholderText("e.g. 691900001")
        # Removed hardcoded border to let global QSS handle the Slate border & Blue focus ring
        self.input_field.setStyleSheet("font-family: 'Fira Code', 'Consolas', monospace; font-size: 28px; padding: 15px; border-radius: 8px;")
        self.input_field.setAlignment(Qt.AlignCenter)
        self.input_field.setMaxLength(15)
        right_layout.addWidget(self.input_field)
        
        right_layout.addSpacing(30)
        
        save_btn = QPushButton("✅ Validate & Confirm")
        save_btn.setStyleSheet("font-size: 16px; font-weight: bold; padding: 15px; background-color: #10b981; color: white; border-radius: 6px;")
        save_btn.clicked.connect(self.on_save)
        right_layout.addWidget(save_btn)
        
        cancel_btn = QPushButton("❌ Cancel & Rescan")
        cancel_btn.setObjectName("SecondaryBtn")
        cancel_btn.setStyleSheet("font-size: 16px; font-weight: bold; padding: 15px; border: 1px solid #ef4444; color: #ef4444; background-color: transparent; border-radius: 6px;")
        cancel_btn.clicked.connect(self.reject)
        right_layout.addWidget(cancel_btn)
        
        right_layout.addStretch()
        main_layout.addWidget(right_pane, stretch=3) # 30% of modal width

        self.display_image(doc_image)
        
    def display_image(self, img_array):
        if img_array is None:
            self.img_label.setText("Failed to load document preview.")
            return
            
        rgb_image = cv2.cvtColor(img_array, cv2.COLOR_BGR2RGB)
        h, w, ch = rgb_image.shape
        bytes_per_line = ch * w
        qt_img = QImage(rgb_image.data, w, h, bytes_per_line, QImage.Format_RGB888)
        
        pixmap = QPixmap.fromImage(qt_img)
        
        # Scale the document width to fill the scroll area (approx 800px on a 1200px window)
        # Allows for vertical scrolling to read the document comfortably.
        scaled_pixmap = pixmap.scaledToWidth(800, Qt.SmoothTransformation)
        self.img_label.setPixmap(scaled_pixmap)
        
    def on_save(self):
        val = self.input_field.text().strip()
        if not val:
            QMessageBox.warning(self, "Incomplete Data", "Please input the 9-digit Exam ID.")
            return
        self.exam_id = val
        self.accept()
