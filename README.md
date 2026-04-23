# Exam Registration System

Exam Registration System is a Windows desktop application that helps staff verify exam applicants by scanning QR codes, logging into the OCSC web portal, capturing applicant evidence, and confirming the Exam ID before saving the final records.

## Overview

When the app runs, it:

1. Opens the camera preview.
2. Logs into the OCSC scraper session automatically.
3. Waits for QR Code scanner input.
4. Reads the national ID from the QR code and searches the OCSC website.
5. Displays the applicant face and the fetched document image.
6. Lets the operator confirm the Exam ID manually.
7. Saves the evidence images to the output folder.

The application is designed primarily for Windows because it uses Windows keyboard layout handling and Playwright browser automation.

## Main Features

- Live camera preview with camera status monitoring
- Hidden QR input field for scanner-as-keyboard workflows
- Automatic OCSC login and applicant search via Playwright
- Captured document preview after search
- Manual Exam ID confirmation dialog
- Keyboard language indicator in the header
- One-click keyboard language toggle
- QR input normalization for Thai keyboard digit mapping
- Configurable camera, output directory, and timeout settings
- Standard and portable runtime workflows

## Project Structure

```text
.
+-- main.py                  # Application entry point
+-- ui/
|   +-- main_window.py       # Main window and workflow
|   +-- override_modal.py    # Manual Exam ID confirmation dialog
|   +-- settings_dialog.py   # Settings dialog
+-- core/
|   +-- camera.py            # Camera worker thread
|   +-- scraper.py           # Playwright login/search worker thread
|   +-- storage.py           # Evidence file saving
+-- utils/
|   +-- config.py            # config.json load/save helpers
|   +-- keyboard_layout.py   # Keyboard language detection and switching
+-- requirements.txt
+-- build.bat
+-- setup_client.bat
+-- config.json
```

## System Requirements

- Windows 10 or Windows 11
- Python 3.12
- A camera device visible through `QMediaDevices`
- Internet access for the OCSC website
- A QR scanner that behaves like keyboard input

## Normal Installation

### 1. Install Python

Install Python 3.12 x64 first.

### 2. Create a virtual environment

```bat
python -m venv venv
```

### 3. Install dependencies

```bat
venv\Scripts\python.exe -m pip install --upgrade pip
venv\Scripts\python.exe -m pip install -r requirements.txt python-dotenv
```

### 4. Install Playwright Chromium

```bat
set PLAYWRIGHT_BROWSERS_PATH=%CD%\ms-playwright
venv\Scripts\python.exe -m playwright install chromium
```

### 5. Run the app

```bat
venv\Scripts\python.exe main.py
```

## Automated Client Setup

`setup_client.bat` is meant for client machines. It:

1. Finds Python 3.12 automatically.
2. Creates a virtual environment.
3. Installs Python packages.
4. Installs Playwright Chromium.
5. Verifies that the runtime is ready.

You can run it by double-clicking `setup_client.bat`.

## Portable Build

`build.bat` creates a portable package that includes:

- Python runtime
- Application source code
- Playwright Chromium
- Launchers for normal or console startup

Run it with:

```bat
build.bat
```

The build output is placed in:

- `setup_output\ExamRegistrationSystem_Portable_1.0.0`
- `setup_output\ExamRegistrationSystem_Portable_1.0.0.zip`

The portable package includes:

- `StartHere.bat` for the normal launch flow
- `Run_ExamRegistrationSystem.bat` for a quiet launch
- `Run_ExamRegistrationSystem_Console.bat` for a console log window

## Configuration

The app reads and writes `config.json`.

Supported settings:

- `camera_index` - camera index
- `camera_name` - selected camera name
- `output_dir` - folder for saved evidence
- `scraper_timeout_sec` - scraper loading/search timeout in seconds

These values can be edited from the Settings dialog and are saved automatically.

## Saved Evidence

When a search completes successfully, the app saves images to `output_dir`.

Typical files:

- `*_face.jpg` - applicant face capture
- `*_doc.jpg` - fetched document image

If search fails, the app can still save an offline face capture for later review.

## How to Use

1. Launch the app.
2. Check camera status and keyboard language status.
3. If the keyboard is Thai, switch it to English using the header button.
4. Scan the QR code with the scanner.
5. Wait for the search and document preview.
6. Review and confirm the Exam ID in the dialog.
7. Confirm to save the final evidence.

## QR and Thai Keyboard Note

The app normalizes QR input so that if the scanner types digits while the keyboard is set to Thai, the app can convert the Thai-layout characters back into numeric digits before searching.

Supported Thai layout to digit mapping:

- Thai key for the number 1 position -> `1`
- Slash key -> `2`
- Minus key -> `3`
- Thai key for the number 4 position -> `4`
- Thai key for the number 5 position -> `5`
- Thai key for the number 6 position -> `6`
- Thai key for the number 7 position -> `7`
- Thai key for the number 8 position -> `8`
- Thai key for the number 9 position -> `9`
- Thai key for the number 0 position -> `0`

It also maps Thai digits 0-9 in Thai numerals back to `0-9`.

## OCSC Login Configuration

The app uses environment variables for OCSC login credentials:

- `OCSC_USER`
- `OCSC_PASS`

For local testing, the source may include fallback defaults, but in production you should set your own values.

Example `.env`:

```env
OCSC_USER=your_username
OCSC_PASS=your_password
```

## Troubleshooting

### QR scan works, but search fails

- Make sure the keyboard is in English.
- Make sure the scanner is typing the correct digits.
- Check the console log for `Normalized QR input`.
- Confirm that the QR code contains a full 13-digit national ID.

### Camera does not start

- Check whether another app is already using the camera.
- Open Settings and select a different camera.
- Try refreshing the camera list.

### Search times out

- Increase `scraper_timeout_sec` in Settings.
- Check your internet connection.
- Confirm that the OCSC page is still accessible.

### Playwright cannot start Chromium

- Make sure Chromium was installed with `playwright install chromium`.
- For a portable package, keep all extracted files in the same folder.

## Development Notes

The application entry point is `main.py`.

The most important files for workflow changes are:

- `ui/main_window.py`
- `core/scraper.py`
- `core/camera.py`
- `utils/keyboard_layout.py`

You can run a quick syntax check with:

```bat
python -m py_compile main.py ui\main_window.py core\scraper.py core\camera.py utils\keyboard_layout.py
```

## License

No license has been defined yet for this project.
