import sys
import time

import cv2
import numpy as np
from PySide6.QtCore import QThread, Signal

class CameraThread(QThread):
    frame_ready = Signal(np.ndarray)
    error_occurred = Signal(str)

    def __init__(self, camera_index=0, target_fps=15, preview_size=(960, 720)):
        super().__init__()
        self.camera_index = camera_index
        self.target_fps = max(1, int(target_fps))
        self.preview_size = preview_size
        self._is_running = True
        self.cap = None
        self._latest_frame = None
        self._last_emit_ts = 0.0
        self._failed_reads = 0

    def _open_camera(self):
        backend = cv2.CAP_DSHOW if sys.platform.startswith("win") else cv2.CAP_ANY
        cap = cv2.VideoCapture(self.camera_index, backend)

        if not cap.isOpened() and backend != cv2.CAP_ANY:
            cap = cv2.VideoCapture(self.camera_index, cv2.CAP_ANY)

        if cap.isOpened():
            try:
                cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
            except Exception:
                pass

        return cap

    def _build_preview_frame(self, frame):
        if not self.preview_size:
            return frame

        max_width, max_height = self.preview_size
        height, width = frame.shape[:2]
        scale = min(max_width / float(width), max_height / float(height), 1.0)

        if scale >= 1.0:
            return frame

        new_width = max(1, int(width * scale))
        new_height = max(1, int(height * scale))
        return cv2.resize(frame, (new_width, new_height), interpolation=cv2.INTER_AREA)

    def run(self):
        self.cap = self._open_camera()
        if not self.cap.isOpened():
            self.error_occurred.emit(f"Failed to open camera index {self.camera_index}")
            return

        min_interval = 1.0 / float(self.target_fps)

        try:
            while self._is_running and not self.isInterruptionRequested():
                ret, frame = self.cap.read()
                if not ret or frame is None:
                    self._failed_reads += 1
                    if self._failed_reads >= 10:
                        self.error_occurred.emit("Disconnected or failed to read frame.")
                        break
                    self.msleep(40)
                    continue

                self._failed_reads = 0
                self._latest_frame = frame

                now = time.monotonic()
                if now - self._last_emit_ts >= min_interval:
                    self._last_emit_ts = now
                    self.frame_ready.emit(self._build_preview_frame(frame))
                else:
                    self.msleep(1)
        finally:
            if self.cap is not None:
                self.cap.release()
                self.cap = None

    def stop(self):
        self._is_running = False
        self.requestInterruption()

        if self.cap is not None:
            try:
                self.cap.release()
            except Exception:
                pass

        self.wait(1000)

    def get_current_frame(self):
        """
        Synchronously captures the current frame.
        Useful for when the QR code is scanned.
        """
        if self._latest_frame is not None:
            return self._latest_frame.copy()

        if self.cap and self.cap.isOpened():
            ret, frame = self.cap.read()
            if ret:
                self._latest_frame = frame
                return frame.copy()
        return None
