import cv2
import numpy as np
from PySide6.QtCore import QThread, Signal

class CameraThread(QThread):
    frame_ready = Signal(np.ndarray)
    error_occurred = Signal(str)

    def __init__(self, camera_index=0):
        super().__init__()
        self.camera_index = camera_index
        self._is_running = True
        self.cap = None

    def run(self):
        self.cap = cv2.VideoCapture(self.camera_index)
        if not self.cap.isOpened():
            self.error_occurred.emit(f"Failed to open camera index {self.camera_index}")
            return

        while self._is_running:
            ret, frame = self.cap.read()
            if not ret or frame is None:
                self.error_occurred.emit("Disconnected or failed to read frame.")
                break
            
            # Emit the frame
            self.frame_ready.emit(frame)
            
            # Sleep slightly to allow GUI to keep up (~30fps)
            self.msleep(30)
            
        self.cap.release()

    def stop(self):
        self._is_running = False
        self.wait()

    def get_current_frame(self):
        """
        Synchronously captures the current frame.
        Useful for when the QR code is scanned.
        """
        if self.cap and self.cap.isOpened():
            ret, frame = self.cap.read()
            if ret:
                return frame
        return None
