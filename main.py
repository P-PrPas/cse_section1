import sys
from PySide6.QtWidgets import QApplication
from ui.main_window import MainWindow

QSS = """
    * {
        font-family: 'Inter', 'SF Pro Display', 'Segoe UI', -apple-system, sans-serif;
    }
    QMainWindow, QDialog {
        background-color: #0f172a; /* Slate 900 */
    }
    QWidget {
        color: #f8fafc;
    }
    QLabel {
        font-size: 14px;
        color: #cbd5e1;
        background-color: transparent;
    }
    QWidget#Header {
        background-color: #1e293b; /* Slate 800 */
        border-bottom: 1px solid #334155;
    }
    QWidget#Card {
        background-color: #1e293b;
        border-radius: 8px;
        border: 1px solid #334155;
    }
    QLabel#StatusBox {
        background-color: #334155;
        border-radius: 6px;
        padding: 6px 12px;
        font-size: 13px;
    }
    QPushButton {
        background-color: #3b82f6; 
        color: white;
        border-radius: 6px;
        padding: 8px 20px;
        font-weight: bold;
        font-size: 14px;
        border: none;
    }
    QPushButton:hover {
        background-color: #2563eb;
    }
    QPushButton:pressed {
        background-color: #1d4ed8;
    }
    QPushButton#SecondaryBtn {
        background-color: transparent;
        border: 1px solid #64748b;
        color: #cbd5e1;
    }
    QPushButton#SecondaryBtn:hover {
        background-color: rgba(100, 116, 139, 0.1);
        color: #f8fafc;
    }
    QLineEdit, QComboBox {
        background-color: #0f172a;
        border: 1px solid #334155;
        border-radius: 6px;
        padding: 10px;
        color: white;
        font-size: 14px;
    }
    QLineEdit:focus, QComboBox:focus {
        border: 2px solid #3b82f6;
        background-color: #1e293b;
    }
    QProgressBar {
        border: none;
        border-radius: 4px;
        background-color: #0f172a;
        text-align: center;
        max-height: 4px;
    }
    QProgressBar::chunk {
        background-color: #3b82f6;
        border-radius: 4px;
    }
    QTextEdit#Console {
        background-color: #0b1120;
        border: 1px solid #1e293b;
        border-radius: 6px;
        font-family: 'Fira Code', 'Consolas', 'Courier New', monospace;
        font-size: 13px;
        color: #4ade80;
        padding: 8px;
    }
"""

def main():
    app = QApplication(sys.argv)
    app.setStyleSheet(QSS)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
