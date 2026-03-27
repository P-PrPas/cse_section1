import cv2
import time
from datetime import datetime
from PySide6.QtWidgets import (
    QMainWindow,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QMessageBox,
    QProgressBar,
    QTextEdit,
)
from PySide6.QtCore import Qt, QTimer, Signal
from PySide6.QtGui import QImage, QPixmap, QTextCursor

from core.camera import CameraThread
from core.scraper import ScraperThread
from core.storage import StorageManager
from utils.config import load_config
from ui.settings_dialog import SettingsDialog
from ui.override_modal import OverrideModal


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Exam Registration System | Enterprise Verification")
        self.setMinimumSize(1280, 720)

        self.config = load_config()
        self.storage = StorageManager(self.config["output_dir"])

        # State Variables
        self.camera_thread = None
        self.scraper_thread = None
        self.current_face_frame = None
        self.scraped_doc_image = None
        self.history_logs = []
        self.scan_locked = False
        self.scan_lock_notice_shown = False

        self._init_ui()
        self.start_camera()

        # Timers
        self.focus_timer = QTimer(self)
        self.focus_timer.timeout.connect(self.check_system_status)
        self.focus_timer.start(500)

        self.clock_timer = QTimer(self)
        self.clock_timer.timeout.connect(self.update_clock)
        self.clock_timer.start(1000)

    def _init_ui(self):
        central = QWidget()
        main_layout = QVBoxLayout(central)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # ---------------- HEADER ----------------
        header = QWidget()
        header.setObjectName("Header")
        header.setFixedHeight(64)
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(24, 0, 24, 0)

        title = QLabel(
            '<b>Exam Registration System</b> '
            '<span style="font-size:16px; color:#94a3b8; font-weight:normal;">| Enterprise Portal</span>'
        )
        title.setStyleSheet("font-size: 20px; color: #ffffff; background-color: transparent;")
        header_layout.addWidget(title)

        header_layout.addStretch()

        self.clock_label = QLabel("00:00:00")
        self.clock_label.setStyleSheet(
            "font-family: 'Fira Code', 'Consolas', monospace; "
            "font-size:18px; color:#cbd5e1; background-color: transparent; margin-right:15px;"
        )
        header_layout.addWidget(self.clock_label)

        settings_btn = QPushButton("Settings")
        settings_btn.setObjectName("SecondaryBtn")
        settings_btn.clicked.connect(self.open_settings)
        header_layout.addWidget(settings_btn)

        main_layout.addWidget(header)

        # ---------------- CONTENT SPLIT PANE ----------------
        content_widget = QWidget()
        content_layout = QHBoxLayout(content_widget)
        content_layout.setContentsMargins(20, 20, 20, 20)
        content_layout.setSpacing(20)

        # LEFT PANE (60%) : Camera
        left_pane = QWidget()
        left_layout = QVBoxLayout(left_pane)
        left_layout.setContentsMargins(0, 0, 0, 0)

        self.cam_label = QLabel("Initializing Camera Feed...")
        self.cam_label.setAlignment(Qt.AlignCenter)
        self.cam_label.setStyleSheet("background-color: #000; border-radius: 8px; border: 1px solid #334155;")
        left_layout.addWidget(self.cam_label, stretch=1)

        # Hidden QR Input - kept transparent
        self.qr_input = QLineEdit()
        self.qr_input.setStyleSheet("background: transparent; border: none; color: transparent;")
        self.qr_input.returnPressed.connect(self.on_qr_scanned)
        left_layout.addWidget(self.qr_input)

        content_layout.addWidget(left_pane, stretch=6)

        # RIGHT PANE (40%) : Info & Status
        right_pane = QWidget()
        right_layout = QVBoxLayout(right_pane)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(15)

        # 1. System Indicators
        indicators_layout = QHBoxLayout()
        indicators_layout.setSpacing(10)

        self.ind_cam = QLabel("Camera: Online")
        self.ind_cam.setObjectName("StatusBox")
        self.ind_cam.setAlignment(Qt.AlignCenter)
        self.ind_cam.setStyleSheet("font-weight: bold; color: #4ade80;")

        self.ind_scan = QLabel("Scanner: Offline")
        self.ind_scan.setObjectName("StatusBox")
        self.ind_scan.setAlignment(Qt.AlignCenter)
        self.ind_scan.setStyleSheet("font-weight: bold; color: #f87171;")

        indicators_layout.addWidget(self.ind_cam)
        indicators_layout.addWidget(self.ind_scan)
        right_layout.addLayout(indicators_layout)

        # 2. Latest Capture Card
        capture_card = QWidget()
        capture_card.setObjectName("Card")
        cc_layout = QVBoxLayout(capture_card)

        cc_header = QLabel("<b>Latest Capture Info</b>")
        cc_layout.addWidget(cc_header)

        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 0)
        self.progress_bar.hide()
        cc_layout.addWidget(self.progress_bar)

        thumbs_layout = QHBoxLayout()

        face_v = QVBoxLayout()
        self.face_thumb = QLabel("Waiting...")
        self.face_thumb.setFixedSize(160, 160)
        self.face_thumb.setStyleSheet(
            "background-color: #0f172a; border-radius:6px; border:1px solid #334155; color: #64748b;"
        )
        self.face_thumb.setAlignment(Qt.AlignCenter)
        face_v.addWidget(self.face_thumb, alignment=Qt.AlignCenter)

        lbl_face = QLabel("Applicant Face")
        lbl_face.setStyleSheet("color: #cbd5e1; font-size: 14px; background-color: transparent; border: none;")
        lbl_face.setAlignment(Qt.AlignCenter)
        face_v.addWidget(lbl_face)
        thumbs_layout.addLayout(face_v)

        doc_v = QVBoxLayout()
        self.doc_thumb = QLabel("Waiting...")
        self.doc_thumb.setFixedSize(160, 220)
        self.doc_thumb.setStyleSheet(
            "background-color: #0f172a; border-radius:6px; border:1px solid #334155; color: #64748b;"
        )
        self.doc_thumb.setAlignment(Qt.AlignCenter)
        doc_v.addWidget(self.doc_thumb, alignment=Qt.AlignCenter)

        lbl_doc = QLabel("Scanned Document")
        lbl_doc.setStyleSheet("color: #cbd5e1; font-size: 14px; background-color: transparent; border: none;")
        lbl_doc.setAlignment(Qt.AlignCenter)
        doc_v.addWidget(lbl_doc)
        thumbs_layout.addLayout(doc_v)

        cc_layout.addLayout(thumbs_layout)

        self.exam_id_label = QLabel("Exam ID: -")
        self.exam_id_label.setStyleSheet(
            "font-family: 'Fira Code', 'Consolas', monospace; "
            "font-size: 28px; font-weight:bold; color:#10b981; margin-top: 15px; background-color: transparent;"
        )
        cc_layout.addWidget(self.exam_id_label, alignment=Qt.AlignCenter)

        right_layout.addWidget(capture_card)

        # 3. Actions / Log Card
        log_card = QWidget()
        log_card.setObjectName("Card")
        log_layout = QVBoxLayout(log_card)
        log_layout.addWidget(QLabel("<b>Processing Console</b>"))

        self.console = QTextEdit()
        self.console.setObjectName("Console")
        self.console.setReadOnly(True)
        log_layout.addWidget(self.console)

        right_layout.addWidget(log_card, stretch=1)
        content_layout.addWidget(right_pane, stretch=4)

        main_layout.addWidget(content_widget, stretch=1)
        self.setCentralWidget(central)

    def update_clock(self):
        self.clock_label.setText(datetime.now().strftime("%H:%M:%S"))

    def check_system_status(self):
        if not getattr(self, "scraper_ready", False):
            self.ind_scan.setText("Scanner: Initializing...")
            self.ind_scan.setStyleSheet("font-weight: bold; color: #f59e0b;")
            return

        if self.scan_locked:
            self.ind_scan.setText("Scanner: Busy")
            self.ind_scan.setStyleSheet("font-weight: bold; color: #f59e0b;")
            return

        if self.qr_input.hasFocus():
            self.ind_scan.setText("Scanner: Ready")
            self.ind_scan.setStyleSheet("font-weight: bold; color: #4ade80;")
        else:
            self.ind_scan.setText("Scanner: Offline (Unfocused)")
            self.ind_scan.setStyleSheet("font-weight: bold; color: #f87171;")
            self.qr_input.setFocus()

    # --- Workflows ---
    def set_status(self, msg, color="#3b82f6"):
        self.add_history(f"<span style='color:{color};'>{msg}</span>")

    def add_history(self, text):
        now = datetime.now().strftime("%H:%M:%S")
        self.console.append(f"<span style='color:#64748b;'>[{now}]</span> {text}")
        cursor = self.console.textCursor()
        cursor.movePosition(QTextCursor.End)
        self.console.setTextCursor(cursor)

    def set_scan_lock(self, locked):
        self.scan_locked = locked
        self.qr_input.clear()

        if locked:
            self.qr_input.setEnabled(False)
        else:
            self.scan_lock_notice_shown = False
            self.qr_input.setEnabled(True)
            self.qr_input.setFocus()

        self.check_system_status()

    def start_camera(self):
        if self.camera_thread:
            self.camera_thread.stop()
        if self.scraper_thread:
            self.scraper_thread.stop()

        self.config = load_config()
        idx = self.config.get("camera_index", 0)
        self.camera_thread = CameraThread(camera_index=idx)
        self.camera_thread.frame_ready.connect(self.update_video_frame)
        self.camera_thread.error_occurred.connect(self.on_camera_error)
        self.camera_thread.start()

        self.scraper_ready = False
        self.set_status("Initializing OCSC session... (Logging in)", "#f59e0b")
        self.ind_scan.setText("Scanner: Initializing...")
        self.ind_scan.setStyleSheet("font-weight: bold; color: #f59e0b;")

        timeout = self.config.get("scraper_timeout_sec", 15)
        self.scraper_thread = ScraperThread(timeout_sec=timeout)
        self.scraper_thread.ready.connect(self.on_scraper_ready)
        self.scraper_thread.finished.connect(self.on_scraping_finished)
        self.scraper_thread.error_occurred.connect(self.on_scraping_error)
        self.scraper_thread.start()

        self.ind_cam.setText("Camera: Online")
        self.ind_cam.setStyleSheet("font-weight: bold; color: #4ade80;")
        self.set_scan_lock(False)

    def on_scraper_ready(self):
        self.scraper_ready = True
        self.set_status("OCSC Scraper Ready. Scan to begin.", "#4ade80")
        self.check_system_status()

    def update_video_frame(self, frame):
        display_frame = cv2.resize(frame, (960, 720))
        rgb_img = cv2.cvtColor(display_frame, cv2.COLOR_BGR2RGB)
        h, w, ch = rgb_img.shape
        q_img = QImage(rgb_img.data, w, h, ch * w, QImage.Format_RGB888)
        self.cam_label.setPixmap(
            QPixmap.fromImage(q_img).scaled(self.cam_label.width(), self.cam_label.height(), Qt.KeepAspectRatio)
        )

    def on_camera_error(self, err_msg):
        self.ind_cam.setText("Camera: Error")
        self.ind_cam.setStyleSheet("font-weight: bold; color: #f87171;")
        self.set_status(f"Camera Error: {err_msg}", "#ef4444")
        self.scan_locked = True
        self.qr_input.setEnabled(False)

    def open_settings(self):
        dlg = SettingsDialog(self)
        if dlg.exec():
            self.start_camera()
            self.config = load_config()
            self.storage.output_dir = self.config["output_dir"]

    def on_qr_scanned(self):
        national_id = self.qr_input.text().strip()
        self.qr_input.clear()
        if not national_id:
            return

        if self.scan_locked:
            self.set_status(
                f"Scanner busy. Ignored QR input: {national_id}. Waiting for current popup/process to finish.",
                "#f59e0b",
            )
            self.scan_lock_notice_shown = True
            return

        if not getattr(self, "scraper_ready", False):
            self.set_status("Scraper is still initializing. Please wait.", "#f59e0b")
            return

        self.current_national_id = national_id
        self.set_scan_lock(True)
        self.set_status(f"Capturing face & Searching ID: {national_id}", "#3b82f6")
        self.current_face_frame = self.camera_thread.get_current_frame()
        if self.current_face_frame is None:
            self.set_status("Failed to capture face. Please try again.", "#ef4444")
            self.set_scan_lock(False)
            return

        self.progress_bar.show()
        self.scraper_thread.search_national_id(national_id)

    def on_scraping_finished(self, doc_image):
        self.progress_bar.hide()
        self.scraped_doc_image = doc_image
        self.set_status("Document fetched successfully. Verify the Exam ID.", "#f59e0b")

        dlg = OverrideModal(self.scraped_doc_image, self, prefill_id=getattr(self, "current_national_id", None))
        if dlg.exec() and dlg.exam_id:
            self.save_final_files(dlg.exam_id)
        else:
            self.set_status("Scan cancelled.", "#ef4444")
            self.reset_standby()

    def on_scraping_error(self, err_msg):
        self.progress_bar.hide()
        self.set_status("Failed to fetch document.", "#ef4444")
        face_path, _ = self.storage.save_capture(None, self.current_face_frame, None, is_offline=True)
        self.add_history("Scraping Network Error")
        QMessageBox.warning(self, "Network Failure", f"Failed to fetch document!\nApplicant face saved to:\n{face_path}")
        self.reset_standby()

    def save_final_files(self, exam_id):
        self.storage.save_capture(exam_id, self.current_face_frame, self.scraped_doc_image)
        self.set_status("File details successfully recorded.", "#22c55e")
        self.exam_id_label.setText(f"Exam ID: {exam_id}")
        self.add_history(f"Registered ID: {exam_id}")

        if self.current_face_frame is not None:
            face_rgb = cv2.cvtColor(cv2.resize(self.current_face_frame, (160, 160)), cv2.COLOR_BGR2RGB)
            h, w, c = face_rgb.shape
            self.face_thumb.setPixmap(QPixmap.fromImage(QImage(face_rgb.data, w, h, c * w, QImage.Format_RGB888)))

        if self.scraped_doc_image is not None:
            doc_rgb = cv2.cvtColor(cv2.resize(self.scraped_doc_image, (160, 220)), cv2.COLOR_BGR2RGB)
            h, w, c = doc_rgb.shape
            self.doc_thumb.setPixmap(QPixmap.fromImage(QImage(doc_rgb.data, w, h, c * w, QImage.Format_RGB888)))

        self.reset_standby()

    def reset_standby(self):
        self.current_face_frame = None
        self.scraped_doc_image = None
        self.face_thumb.clear()
        self.face_thumb.setText("Waiting...")
        self.doc_thumb.clear()
        self.doc_thumb.setText("Waiting...")
        self.exam_id_label.setText("Exam ID: -")
        self.set_scan_lock(self.ind_cam.text() == "Camera: Error")
        self.set_status("Awaiting Scanner Input...", "#4ade80")

    def closeEvent(self, event):
        if self.camera_thread:
            self.camera_thread.stop()
        if getattr(self, "scraper_thread", None):
            self.scraper_thread.stop()
        super().closeEvent(event)
