from PySide6.QtCore import QThread, Signal
from playwright.sync_api import sync_playwright
import numpy as np
import cv2
import queue
import os
import traceback
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

class ScraperThread(QThread):
    finished = Signal(np.ndarray)  # Emits the screenshot as CV2 array
    error_occurred = Signal(str)
    ready = Signal()               # Emitted when login is complete

    def __init__(self, timeout_sec=15):
        super().__init__()
        self.timeout_sec = timeout_sec
        self.cmd_queue = queue.Queue()
        self._is_running = True

    def run(self):
        try:
            with sync_playwright() as p:
                browser = p.chromium.launch(headless=True)
                # Ensure the viewport is large enough to capture the ID card layout
                context = browser.new_context(viewport={"width": 1280, "height": 1080})
                page = context.new_page()
                
                # 1. Login Phase
                login_url = "https://job3.ocsc.go.th/OCSRegisterWeb/checkphoto"
                page.goto(login_url, timeout=self.timeout_sec * 1000)
                
                user = os.environ.get("OCSC_USER", "eexamphoto")
                pw = os.environ.get("OCSC_PASS", "zLc3R/IZNfapHG5Idk2T3A==")
                
                page.get_by_placeholder("กรุณาระบุชื่อผู้ใช้").fill(user)
                page.locator("input[formcontrolname='password']").fill(pw)
                page.get_by_role("button", name="เข้าสู่ระบบ").click()
                
                # Wait for search box to ensure login succeeded
                search_box = page.get_by_placeholder("เลขประจำตัวประชาชน")
                search_box.wait_for(state="visible", timeout=self.timeout_sec * 1000)
                
                self.ready.emit()

                # 2. Main Event Loop
                while self._is_running:
                    try:
                        national_id = self.cmd_queue.get(timeout=1.0)
                        if national_id is None: # Exit signal
                            break
                        
                        self._process_search(page, national_id)
                        
                    except queue.Empty:
                        continue
                        
                browser.close()
                
        except Exception as e:
            traceback.print_exc()
            self.error_occurred.emit(f"Scraper error: {str(e)}")
            
    def _process_search(self, page, national_id):
        try:
            search_box = page.get_by_placeholder("เลขประจำตัวประชาชน")
            search_box.fill(national_id)
            
            # Click search button
            page.locator("button:has-text('ค้นหา')").click()
            
            # Since Angular/SPA might not always trigger full networkidle,
            # we also do a small manual wait and wait for specific DOM mutations if possible.
            page.wait_for_load_state("networkidle", timeout=self.timeout_sec * 1000)
            page.wait_for_timeout(1500)  # Extra buffer to ensure UI rendered completely
            
            # Capture viewport for the result
            # We don't do full_page=True because the result might just be neatly inside the viewport
            screenshot_bytes = page.screenshot(full_page=False, type="jpeg")
            
            nparr = np.frombuffer(screenshot_bytes, np.uint8)
            img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
            
            self.finished.emit(img)
            
        except Exception as e:
            traceback.print_exc()
            self.error_occurred.emit(f"Search failed: {str(e)}")

    def search_national_id(self, national_id):
        """Called safely from main thread to enqueue a search command"""
        self.cmd_queue.put(national_id)

    def stop(self):
        """Called to gracefully shut down the thread"""
        self._is_running = False
        self.cmd_queue.put(None)
        self.wait()
