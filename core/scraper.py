from PySide6.QtCore import QThread, Signal
from playwright.sync_api import sync_playwright
import numpy as np
import cv2

class ScraperThread(QThread):
    finished = Signal(np.ndarray)  # Emits the screenshot as CV2 array
    error_occurred = Signal(str)

    def __init__(self, url, timeout_sec=15):
        super().__init__()
        self.url = url
        self.timeout_sec = timeout_sec

    def run(self):
        try:
            with sync_playwright() as p:
                browser = p.chromium.launch(headless=True)
                # Use a massive viewport so internal scrolling containers (like in Google Drive or job3)
                # are fully expanded natively, capturing up to ~3 A4 pages consistently.
                context = browser.new_context(viewport={"width": 1280, "height": 3000})
                page = context.new_page()
                
                # Navigate and wait until network is idle
                response = page.goto(self.url, timeout=self.timeout_sec * 1000)
                
                # Check for URL Shortener Ads / Redirects (e.g. q.me, meqr)
                import re
                original_url = self.url.lower()
                if "q.me" in original_url or "short" in original_url or "qr" in original_url:
                    # Wait up to 10 seconds for ad redirects or clicking "Skip"
                    for _ in range(10):
                        current_url = page.url.lower()
                        # If reached the real site (e.g. job3.ocsc.go.th) or a PDF file
                        if "job3.ocsc.go.th" in current_url or current_url.endswith(".pdf"):
                            break
                        
                        try:
                            # Aggressive search for any element containing Skip/Continue/ข้าม
                            skip_pattern = re.compile(r"skip|continue|ข้าม|ไปต่อ", re.IGNORECASE)
                            elements = page.get_by_text(skip_pattern).all()
                            for el in elements:
                                if el.is_visible():
                                    el.click(timeout=500, force=True)
                        except Exception:
                            pass
                        
                        page.wait_for_timeout(1000)
                
                # Wait for final destination to fully load
                page.wait_for_load_state("networkidle", timeout=self.timeout_sec * 1000)
                
                if response is None or not response.ok:
                    status = response.status if response else "Unknown"
                    self.error_occurred.emit(f"Failed to load URL (Status: {status})")
                    browser.close()
                    return

                # Capture full page screenshot
                # Because the viewport height is 3000px, it captures almost everything natively
                # without needing CSS hacks for nested scrolling divs!
                screenshot_bytes = page.screenshot(full_page=True, type="jpeg")
                browser.close()

                # Convert to numpy array for OpenCV
                nparr = np.frombuffer(screenshot_bytes, np.uint8)
                img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
                
                self.finished.emit(img)
                
        except Exception as e:
            self.error_occurred.emit(f"Scraper error: {str(e)}")
