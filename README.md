# Flaky USB Recover Tool

A Windows-focused recovery helper for unstable USB drives that repeatedly disconnect.

The tool monitors removable drives, lets you select the target USB once, then keeps re-scanning and copying files whenever the device reconnects. Already copied files are skipped by size check.

## Features

- Detects newly plugged USB drives.
- Shows drive metadata before you confirm the target.
- Recovers files in chunks and uses `.part` temporary files for safer interrupted copies.
- Re-arms automatically after disconnection and continues from where it left off.
- Excludes common protected folders (`System Volume Information`, `$Recycle.Bin`) during traversal.

## Quick Start (No Python Install Required for End Users)

If you download a release that includes `dist/FlakyUSBRecover.exe`:

1. Unzip the release folder.
2. Double-click `Run_USB_Recover.bat`.
3. Follow on-screen instructions.

`Run_USB_Recover.bat` prefers the packaged EXE. If the EXE is missing, it falls back to Python mode.

## Build the Standalone EXE (Maintainers)

Requirements:

- Windows
- Python 3.10+

Steps:

1. Run `build_exe.bat`.
2. Built file will be at `dist/FlakyUSBRecover.exe`.

The EXE can then be attached to a GitHub Release so users do not need Python.

## Python Mode (Developer Fallback)

```bat
python flaky_usb_recover.py
```

Optional arguments:

```text
-o, --output <path>         Destination directory (default: ./Recovered_USB_Files)
--poll-interval <seconds>   USB polling interval (default: 1.0)
--post-mount-delay <sec>    Wait after mount before scan (default: 1.0)
--assume-yes                Auto-select first newly detected USB
--no-color                  Disable ANSI colors
```

## Safety and Limitations

- This is a best-effort copier, not a forensic recovery tool.
- It only copies files currently readable by Windows.
- If the drive fully fails hardware-level reads, specialized recovery tools/services may still be needed.

## Recommended GitHub Release Layout

For user-friendly releases, include:

- `Run_USB_Recover.bat`
- `dist/FlakyUSBRecover.exe`
- `README.md`

This gives non-technical users a double-click start path.
