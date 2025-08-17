# RimWorld Trait Auto-Roller

Automatically clicks the Randomize button in RimWorld's pawn creation screen until desired trait combinations appear.

## Features

- **Auto-clicking** with customizable speed (default 25ms delay)
- **OCR trait detection** using Tesseract
- **Combo detection**: Stops when finding ONE trait from "MUST HAVE" list AND ONE from secondary list
- **Smart pausing**: Pauses for 5 seconds when finding a MUST HAVE trait without secondary trait
- **Visual overlay** showing capture region
- **Resizable trait lists** with scrollbars
- **Save/Load configuration**
- **Optional OCR logging** for debugging
- **File logging** to `rimworld_log.txt`

## Requirements

```bash
pip install pytesseract pillow opencv-python numpy pyautogui keyboard
```

Also requires [Tesseract OCR](https://github.com/UB-Mannheim/tesseract/wiki) installed at `C:\Program Files\Tesseract-OCR\`

## Usage

1. Run the script: `python rimworld_final.py`
2. Position the overlay window where convenient
3. Press **F7** while hovering over the Randomize button in RimWorld
4. Press **F9** to start/stop auto-rolling

## Configuration

### Default MUST HAVE traits (requires ONE):
- tough
- iron willed  
- industrious

### Default secondary traits (requires ONE):
- jogger, nimble, quick sleeper, sanguine, kind
- brawler, great memory, masochist, super immune
- hard worker, fast learner, bloodlust, undergrounder
- fast walker, optimist, steadfast
- psychically hypersensitive, psychically sensitive

Edit lists directly in the UI. Configuration saves to `rimworld_config.json`.

## Controls

- **F7**: Set Randomize button position
- **F9**: Start/Stop rolling
- **Save Config**: Save current trait lists
- **Load Config**: Load saved trait lists
- **Open Log**: Open log file in Notepad++
- **Log OCR** checkbox: Enable/disable OCR text logging (disabled for speed)

## How it Works

1. Takes screenshot of trait area (770px left, 280px down from Randomize button)
2. Uses OCR to read trait names
3. Checks if ONE trait from MUST HAVE list AND ONE from secondary list are present
4. If combo found: stops and alerts
5. If only MUST HAVE found: pauses 5 seconds for user to decide
6. Otherwise: clicks Randomize and continues

## Performance

- Optimized for speed with minimal OCR processing
- Async logging to prevent blocking
- Pre-compiled trait lists
- Early exit optimization in trait checking

## Notes

- All trait names are normalized to lowercase without hyphens
- The red overlay briefly shows the capture region when setting position
- Logs are written to `rimworld_log.txt` for debugging