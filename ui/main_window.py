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
from PySide6.QtCore import Qt, QTimer
from PySide6.QtMultimedia import QMediaDevices
from PySide6.QtGui import QImage, QPixmap, QTextCursor

from core.camera import CameraThread
from core.scraper import ScraperThread
from core.storage import StorageManager
from utils.config import load_config
from utils.keyboard_layout import (
    get_current_keyboard_language,
    normalize_scanned_national_id,
    toggle_keyboard_language,
)
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
        self.last_camera_frame_ts = time.monotonic()
        self._keyboard_notice_shown = False

        self._init_ui()
        self.start_services()

        # Timers
        self.focus_timer = QTimer(self)
        self.focus_timer.timeout.connect(self.check_system_status)
        self.focus_timer.start(500)

        QTimer.singleShot(0, self.show_keyboard_language_notice)

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

        self.keyboard_button = QPushButton("Keyboard: --")
        self.keyboard_button.setObjectName("SecondaryBtn")
        self.keyboard_button.setCursor(Qt.PointingHandCursor)
        self.keyboard_button.clicked.connect(self.toggle_keyboard_layout)
        header_layout.addWidget(self.keyboard_button)

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
            self.refresh_keyboard_indicator()
            return

        if self.scan_locked:
            self.ind_scan.setText("Scanner: Busy")
            self.ind_scan.setStyleSheet("font-weight: bold; color: #f59e0b;")
            self.refresh_keyboard_indicator()
            return

        if self.qr_input.hasFocus():
            self.ind_scan.setText("Scanner: Ready")
            self.ind_scan.setStyleSheet("font-weight: bold; color: #4ade80;")
        else:
            self.ind_scan.setText("Scanner: Offline (Unfocused)")
            self.ind_scan.setStyleSheet("font-weight: bold; color: #f87171;")
            self.qr_input.setFocus()

        if self.camera_thread and self.camera_thread.isRunning():
            if time.monotonic() - self.last_camera_frame_ts > 10:
                self.set_status("Camera stream stalled. Restarting camera...", "#f59e0b")
                self.restart_camera()
                self.refresh_keyboard_indicator()
                return

        self.refresh_keyboard_indicator()

    # --- Workflows ---
    def set_status(self, msg, color="#3b82f6"):
        self.add_history(f"<span style='color:{color};'>{msg}</span>")

    def add_history(self, text):
        now = datetime.now().strftime("%H:%M:%S")
        self.console.append(f"<span style='color:#64748b;'>[{now}]</span> {text}")
        cursor = self.console.textCursor()
        cursor.movePosition(QTextCursor.End)
        self.console.setTextCursor(cursor)

    def refresh_keyboard_indicator(self):
        language = get_current_keyboard_language()
        if language == "Thai":
            self.keyboard_button.setText("Keyboard: Thai")
            self.keyboard_button.setStyleSheet(
                "QPushButton {"
                "background-color: rgba(239, 68, 68, 0.18);"
                "border: 1px solid rgba(248, 113, 113, 0.65);"
                "color: #fecaca;"
                "padding: 8px 14px;"
                "border-radius: 6px;"
                "font-weight: bold;"
                "}"
                "QPushButton:hover { background-color: rgba(239, 68, 68, 0.28); }"
            )
        elif language == "English":
            self.keyboard_button.setText("Keyboard: English")
            self.keyboard_button.setStyleSheet(
                "QPushButton {"
                "background-color: rgba(34, 197, 94, 0.16);"
                "border: 1px solid rgba(74, 222, 128, 0.65);"
                "color: #bbf7d0;"
                "padding: 8px 14px;"
                "border-radius: 6px;"
                "font-weight: bold;"
                "}"
                "QPushButton:hover { background-color: rgba(34, 197, 94, 0.26); }"
            )
        else:
            self.keyboard_button.setText(f"Keyboard: {language}")
            self.keyboard_button.setStyleSheet(
                "QPushButton {"
                "background-color: rgba(100, 116, 139, 0.16);"
                "border: 1px solid rgba(148, 163, 184, 0.55);"
                "color: #e2e8f0;"
                "padding: 8px 14px;"
                "border-radius: 6px;"
                "font-weight: bold;"
                "}"
            )

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

    def start_services(self):
        self.start_camera()
        self.start_scraper()

    def _resolve_camera_index(self):
        desired_name = (self.config.get("camera_name") or "").strip()
        desired_index = int(self.config.get("camera_index", 0))

        if desired_name:
            for idx, cam in enumerate(QMediaDevices.videoInputs()):
                if (cam.description() or "").strip() == desired_name:
                    return idx

        return desired_index

    def start_camera(self):
        if self.camera_thread:
            self.camera_thread.stop()

        self.last_camera_frame_ts = time.monotonic()
        idx = self._resolve_camera_index()
        cameras = QMediaDevices.videoInputs()
        camera_name = ""
        if 0 <= idx < len(cameras):
            camera_name = cameras[idx].description() or ""
        if not camera_name:
            camera_name = self.config.get("camera_name") or f"Index {idx}"

        self.camera_thread = CameraThread(camera_index=idx, target_fps=15, preview_size=(960, 720))
        self.camera_thread.frame_ready.connect(self.update_video_frame)
        self.camera_thread.error_occurred.connect(self.on_camera_error)
        self.camera_thread.start()

        self.ind_cam.setText(f"Camera: Online ({camera_name})")
        self.ind_cam.setStyleSheet("font-weight: bold; color: #4ade80;")
        self.set_scan_lock(False)

    def start_scraper(self):
        if self.scraper_thread:
            self.scraper_thread.stop()

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

    def restart_camera(self):
        if self.camera_thread:
            self.camera_thread.stop()

        self.last_camera_frame_ts = time.monotonic()
        idx = self._resolve_camera_index()
        cameras = QMediaDevices.videoInputs()
        camera_name = ""
        if 0 <= idx < len(cameras):
            camera_name = cameras[idx].description() or ""
        if not camera_name:
            camera_name = self.config.get("camera_name") or f"Index {idx}"

        self.camera_thread = CameraThread(camera_index=idx, target_fps=15, preview_size=(960, 720))
        self.camera_thread.frame_ready.connect(self.update_video_frame)
        self.camera_thread.error_occurred.connect(self.on_camera_error)
        self.camera_thread.start()

        self.ind_cam.setText(f"Camera: Online ({camera_name})")
        self.ind_cam.setStyleSheet("font-weight: bold; color: #4ade80;")
        self.set_scan_lock(False)

    def show_keyboard_language_notice(self):
        if self._keyboard_notice_shown:
            return

        self._keyboard_notice_shown = True
        language = get_current_keyboard_language()
        if language == "Thai":
            QMessageBox.warning(
                self,
                "Keyboard Language Warning",
                "Current keyboard language is Thai.\n\n"
                "Please switch to English before scanning QR codes.\n"
                "You can click the Keyboard button in the header to toggle it.",
            )
            self.add_history("Keyboard language detected: Thai")
        else:
            QMessageBox.information(
                self,
                "Keyboard Language",
                f"Current keyboard language is {language}.\n\n"
                "You can click the Keyboard button in the header to toggle it.",
            )
            self.add_history(f"Keyboard language detected: {language}")

        self.refresh_keyboard_indicator()

    def toggle_keyboard_layout(self):
        if toggle_keyboard_language():
            language = get_current_keyboard_language()
            self.refresh_keyboard_indicator()
            self.set_status(f"Keyboard language switched to {language}.", "#4ade80")
            self.add_history(f"Keyboard language switched to {language}")
        else:
            QMessageBox.warning(self, "Keyboard Language", "Unable to change keyboard language on this machine.")

    def on_scraper_ready(self):
        self.scraper_ready = True
        self.set_status("OCSC Scraper Ready. Scan to begin.", "#4ade80")
        self.check_system_status()

    def update_video_frame(self, frame):
        if frame is None:
            return

        self.last_camera_frame_ts = time.monotonic()
        rgb_img = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
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
        self.last_camera_frame_ts = 0.0
        self.refresh_keyboard_indicator()

    def open_settings(self):
        previous_camera_index = self.config.get("camera_index", 0)
        previous_camera_name = self.config.get("camera_name", "")
        dlg = SettingsDialog(self)
        if dlg.exec():
            self.config = load_config()
            if self.camera_thread:
                self.camera_thread.camera_index = self.config.get("camera_index", 0)
            if self.scraper_thread:
                self.scraper_thread.timeout_sec = self.config.get("scraper_timeout_sec", 15)
            self.storage.output_dir = self.config["output_dir"]
            if (
                self.config.get("camera_index", 0) != previous_camera_index
                or self.config.get("camera_name", "") != previous_camera_name
            ):
                self.start_camera()
            self.refresh_keyboard_indicator()

    def on_qr_scanned(self):
        raw_input = self.qr_input.text().strip()
        national_id = normalize_scanned_national_id(raw_input)
        self.qr_input.clear()
        if not national_id:
            return

        if raw_input != national_id:
            self.add_history(f"Normalized QR input: {raw_input} -> {national_id}")

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
