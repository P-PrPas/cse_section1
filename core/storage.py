import os
import cv2
from datetime import datetime

class StorageManager:
    def __init__(self, output_dir):
        self.output_dir = output_dir
        if not os.path.exists(self.output_dir):
            os.makedirs(self.output_dir)

    def save_capture(self, user_id, face_frame, doc_frame, is_offline=False):
        """
        Saves the face and document frames to the output directory.
        If is_offline is True, doc_frame can be None and the face is saved with an offline timestamp.
        Returns a tuple of paths (face_path, doc_path).
        """
        try:
            if is_offline or not user_id:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                face_filename = f"Offline_{timestamp}_face.jpg"
                doc_filename = None
            else:
                face_filename = f"{user_id}_face.jpg"
                doc_filename = f"{user_id}_doc.jpg"

            face_path = os.path.join(self.output_dir, face_filename)
            cv2.imwrite(face_path, face_frame)

            doc_path = None
            if doc_frame is not None and doc_filename:
                doc_path = os.path.join(self.output_dir, doc_filename)
                cv2.imwrite(doc_path, doc_frame)

            return face_path, doc_path
        except Exception as e:
            print(f"Error saving files: {e}")
            return None, None
