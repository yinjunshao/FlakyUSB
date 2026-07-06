import os
import sys
import time
import json
import subprocess
import argparse

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DEFAULT_OUTPUT_DIR = os.path.join(SCRIPT_DIR, "Recovered_USB_Files")

# Enable ANSI colors on Windows
os.system('')

class Colors:
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKCYAN = '\033[96m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'


def ctext(text, color, use_color=True):
    if not use_color:
        return text
    return f"{color}{text}{Colors.ENDC}"


def print_banner(use_color=True):
    banner = ctext(f"""
=========================================================
      FLAKY USB RECOVERY TOOL (V1.0) - IDLE MONITOR      
=========================================================
""", f"{Colors.OKCYAN}{Colors.BOLD}", use_color=use_color)
    print(banner)


def _run_powershell_json(ps_cmd):
    """Run a PowerShell command that outputs JSON and return parsed Python data."""
    output = subprocess.check_output(
        [
            'powershell',
            '-NoProfile',
            '-ExecutionPolicy',
            'Bypass',
            '-Command',
            ps_cmd,
        ],
        text=True,
        stderr=subprocess.DEVNULL,
    ).strip()

    if not output:
        return []

    data = json.loads(output)
    if isinstance(data, dict):
        return [data]
    if isinstance(data, list):
        return data
    return []


def get_usb_drives():
    """Returns a dictionary of USB drives currently plugged in."""
    drives = {}

    ps_cmd = (
        "$d = Get-CimInstance Win32_LogicalDisk -Filter \"DriveType=2\" | "
        "Select-Object DeviceID, VolumeName, VolumeSerialNumber; "
        "$d | ConvertTo-Json -Compress"
    )

    try:
        for item in _run_powershell_json(ps_cmd):
            device_id = (item.get('DeviceID') or '').strip()
            if not device_id:
                continue
            drives[device_id] = {
                'name': (item.get('VolumeName') or '').strip(),
                'serial': (item.get('VolumeSerialNumber') or '').strip() or 'UNKNOWN',
            }
        return drives
    except Exception:
        # Fallback for older systems where CIM/PowerShell JSON parsing may fail.
        try:
            output = subprocess.check_output(
                'wmic logicaldisk where drivetype=2 get deviceid,volumename,volumeserialnumber /format:csv',
                shell=True,
                text=True,
                stderr=subprocess.DEVNULL,
            )
        except subprocess.CalledProcessError:
            output = ""

        for line in output.split('\n'):
            line = line.strip()
            if line and not line.startswith('Node') and ',' in line:
                parts = line.split(',')
                if len(parts) >= 4:
                    _, device_id, volume_name, vol_serial = parts[0], parts[1], parts[2], parts[3]
                    if device_id:
                        drives[device_id] = {
                            'name': (volume_name or '').strip(),
                            'serial': (vol_serial or '').strip() or 'UNKNOWN',
                        }

    return drives


def get_drive_info(drive_letter, use_color=True):
    """Fetches detailed info about the drive using PowerShell."""
    print(ctext(f"[*] Fetching detailed device information for {drive_letter}...", Colors.OKBLUE, use_color))
    try:
        ps_cmd = (
            f"Get-CimInstance Win32_LogicalDisk -Filter \"DeviceID='{drive_letter}'\" | "
            "Format-List *"
        )
        info = subprocess.check_output(
            ['powershell', '-NoProfile', '-ExecutionPolicy', 'Bypass', '-Command', ps_cmd],
            text=True,
            stderr=subprocess.DEVNULL,
        )
        print(ctext(info.strip(), Colors.HEADER, use_color))
    except Exception as e:
        print(ctext(f"[!] Could not fetch extended info: {e}", Colors.FAIL, use_color))


def safe_copy(src, dst, use_color=True):
    """Copies a file safely, robust to disconnections."""
    try:
        if not os.path.exists(src):
            return False

        if os.path.exists(dst):
            src_size = os.path.getsize(src)
            dst_size = os.path.getsize(dst)
            if src_size == dst_size:
                return True  # Already copied

        # Ensure dir exists
        os.makedirs(os.path.dirname(dst), exist_ok=True)

        # We copy in chunks so if it fails, we don't think it succeeded
        temp_dst = dst + ".part"
        with open(src, 'rb') as fsrc, open(temp_dst, 'wb') as fdst:
            while True:
                chunk = fsrc.read(1024 * 1024 * 4)  # 4MB chunks
                if not chunk:
                    break
                fdst.write(chunk)

        os.replace(temp_dst, dst)
        print(ctext(f"[+] Copied: {src}", Colors.OKGREEN, use_color))
        return True
    except Exception as e:
        print(ctext(f"[!] Failed to copy {src}: {e}", Colors.FAIL, use_color))
        if 'temp_dst' in locals() and os.path.exists(temp_dst):
            try:
                os.remove(temp_dst)
            except Exception:
                pass
        return False


def recover_drive(drive_letter, output_dir, post_mount_delay=1.0, use_color=True):
    """Recursively copies files from the drive to the output directory."""
    print(ctext(f"\n>>> STARTING RECOVERY FOR {drive_letter} <<<", f"{Colors.WARNING}{Colors.BOLD}", use_color))
    time.sleep(post_mount_delay)  # Give it a second to stabilize after mount

    if not os.path.exists(drive_letter + "\\"):
        print(ctext(f"[!] Drive {drive_letter} vanished before we could start.", Colors.FAIL, use_color))
        return

    def _walk_error(err):
        print(ctext(f"[!] Skipping inaccessible path: {err}", Colors.WARNING, use_color))

    for root, dirs, files in os.walk(drive_letter + "\\", onerror=_walk_error):
        # Avoid expensive or protected directories that often fail on removable media.
        dirs[:] = [d for d in dirs if d.lower() not in {'system volume information', '$recycle.bin'}]

        for file in files:
            src_path = os.path.join(root, file)
            rel_path = os.path.relpath(src_path, drive_letter + "\\")
            dst_path = os.path.join(output_dir, rel_path)

            # Check if drive is still there before attempting next file
            if not os.path.exists(drive_letter + "\\"):
                print(ctext("[!] Drive disconnected during enumeration!", Colors.FAIL, use_color))
                return

            try:
                needs_copy = (not os.path.exists(dst_path)) or (os.path.getsize(src_path) != os.path.getsize(dst_path))
            except Exception:
                needs_copy = True

            if needs_copy:
                success = safe_copy(src_path, dst_path, use_color=use_color)
                if not success:
                    # Likely disconnected
                    if not os.path.exists(drive_letter + "\\"):
                        print(ctext("[!] Drive disconnected during copy! Waiting for replug...", Colors.FAIL, use_color))
                        return

    print(ctext(">>> RECOVERY COMPLETE OR DRIVE FULLY SCANNED <<<", f"{Colors.OKGREEN}{Colors.BOLD}", use_color))


def parse_args():
    parser = argparse.ArgumentParser(
        description="Recover files from flaky USB drives by repeatedly scanning after reconnects."
    )
    parser.add_argument(
        '-o',
        '--output',
        default=DEFAULT_OUTPUT_DIR,
        help='Destination folder for recovered files (default: ./Recovered_USB_Files).',
    )
    parser.add_argument(
        '--poll-interval',
        type=float,
        default=1.0,
        help='Seconds between USB presence checks (default: 1.0).',
    )
    parser.add_argument(
        '--post-mount-delay',
        type=float,
        default=1.0,
        help='Seconds to wait after mount before scanning (default: 1.0).',
    )
    parser.add_argument(
        '--assume-yes',
        action='store_true',
        help='Auto-select the first newly detected USB target without prompt.',
    )
    parser.add_argument(
        '--no-color',
        action='store_true',
        help='Disable ANSI colors in output.',
    )
    return parser.parse_args()


def main():
    args = parse_args()
    use_color = not args.no_color

    print_banner(use_color=use_color)
    print(ctext("[*] Initializing state. Please ensure the broken USB is UNPLUGGED.", Colors.OKBLUE, use_color))
    
    initial_drives = get_usb_drives()
    target_serial = None
    output_dir = os.path.abspath(args.output)
    
    print(f"[*] Currently detected USBs: {list(initial_drives.keys())}")
    print(f"[*] Waiting for a NEW USB to be plugged in...")
    
    # Phase 1: Wait for target USB
    while target_serial is None:
        current_drives = get_usb_drives()
        new_drives = set(current_drives.keys()) - set(initial_drives.keys())
        
        for drive in new_drives:
            print(ctext(f"\n>>> NEW USB DETECTED: {drive} <<<", Colors.WARNING, use_color))
            info = current_drives[drive]
            print(f"    Name:   {info['name']}")
            print(f"    Serial: {info['serial']}")
            
            get_drive_info(drive, use_color=use_color)
            
            if args.assume_yes:
                ans = 'Y'
                print("[*] --assume-yes enabled: target auto-selected.")
            else:
                ans = input(ctext("\nIs this the correct USB to recover? (Y/N): ", Colors.OKCYAN, use_color)).strip().upper()

            if ans == 'Y':
                target_serial = info['serial']
                print(ctext(f"[*] TARGET ACQUIRED! Serial: {target_serial}", Colors.OKGREEN, use_color))
                print(f"[*] Files will be saved to: {output_dir}")
                break
            else:
                print(f"[*] Ignored {drive}. Update baseline...")
                initial_drives = current_drives
        
        time.sleep(max(0.2, args.poll_interval))
        initial_drives = current_drives  # Update baseline
        
    # Phase 2: Armed and waiting
    print(ctext("\n[=================================================]", f"{Colors.BOLD}{Colors.OKGREEN}", use_color))
    print(ctext("[                 SYSTEM ARMED                    ]", f"{Colors.BOLD}{Colors.OKGREEN}", use_color))
    print(ctext("[=================================================]", f"{Colors.BOLD}{Colors.OKGREEN}", use_color))
    print(f"[*] Monitoring for USB with serial {target_serial}...")
    
    os.makedirs(output_dir, exist_ok=True)
    
    while True:
        current_drives = get_usb_drives()
        target_drive = None
        
        # Find if our target is plugged in
        for dl, info in current_drives.items():
            if info['serial'] == target_serial:
                target_drive = dl
                break
                
        if target_drive:
            recover_drive(
                target_drive,
                output_dir,
                post_mount_delay=max(0.0, args.post_mount_delay),
                use_color=use_color,
            )
            # Wait until it is unplugged to prevent spamming
            print(ctext("[*] Waiting for drive to be unplugged or power-cycled...", Colors.OKBLUE, use_color))
            while target_drive in get_usb_drives():
                time.sleep(max(0.2, args.poll_interval))
            print(ctext("[!] Drive is gone. System re-armed and waiting...", Colors.WARNING, use_color))
            
        time.sleep(max(0.2, args.poll_interval))

if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print(f"\n{ctext('[*] Exiting...', Colors.FAIL)}")
        sys.exit(0)
