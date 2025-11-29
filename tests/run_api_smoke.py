#!/usr/bin/env python3
"""
Automated smoke test for SCLController public methods (non-destructive).

This exercises the following against a live controller:
- connect/close (via context manager) and release_network
- check_status, get_play_status, get_free_space, list_files
- create_subdirectory, upload_file, download_file, delete_file, delete_subdirectory
- pause, play, real_time_display, restart_schedule
- set_calendar_clock (sets to current time)

Destructive/persistent operations NOT executed by default:
- format_disk (ERASES DATA)
- reset_controller (reboots controller)
- set_on_off_time, set_power_mode (persistent user-visible behaviour)

Usage:
  python tests/run_api_smoke.py 172.31.16.25
"""
import sys
import tempfile
from pathlib import Path
from datetime import datetime

from scl_protocol import SCLController, SCLControllerError

IP = sys.argv[1] if len(sys.argv) > 1 else None
if not IP:
    print("Usage: run_api_smoke.py <controller_ip>")
    sys.exit(2)

TMP_DIR = Path(tempfile.mkdtemp(prefix="scl_api_test_"))
LOCAL_UPLOAD = TMP_DIR / "TEST_API_UPLOAD.txt"
LOCAL_DOWNLOAD = TMP_DIR / "TEST_API_DOWNLOAD.txt"

REMOTE_SUBDIR = "TST"
REMOTE_FILE = f"{REMOTE_SUBDIR}/TEST_API.TXT"

results = []

def record(name, ok, msg=""):
    status = "PASS" if ok else "FAIL"
    results.append((name, status, msg))
    print(f"[{status}] {name} {('- ' + msg) if msg else ''}")

try:
    LOCAL_UPLOAD.write_text("hello from scl_protocol smoke test\n", encoding="ascii")

    with SCLController(IP) as c:
        # Basic status
        try:
            st = c.check_status()
            record("check_status", True, f"connected={st.get('connected', False)}")
        except Exception as e:
            record("check_status", False, str(e))

        try:
            ps = c.get_play_status()
            record("get_play_status", True, f"driver={ps.get('driver')}, item={ps.get('playlist_item')}")
        except Exception as e:
            record("get_play_status", False, str(e))

        # File system
        try:
            free_a = c.get_free_space('A')
            record("get_free_space(A)", True, f"{free_a} bytes")
        except Exception as e:
            record("get_free_space(A)", False, str(e))

        try:
            files = c.list_files('A', '')
            record("list_files(A,/)", True, f"{len(files)} entries")
        except Exception as e:
            record("list_files(A,/)", False, str(e))

        # Create subdir (ignore if exists)
        created_subdir = False
        try:
            c.create_subdirectory(REMOTE_SUBDIR, 'A')
            created_subdir = True
            record("create_subdirectory(TST)", True)
        except SCLControllerError as e:
            # If already exists, treat as pass
            if "Failed to create" in str(e):
                record("create_subdirectory(TST)", False, str(e))
            else:
                record("create_subdirectory(TST)", True, "already exists or controller reports OK")
        except Exception as e:
            record("create_subdirectory(TST)", False, str(e))

        # Upload file
        try:
            c.upload_file(str(LOCAL_UPLOAD), 'A', REMOTE_FILE, pause_controller=True)
            record("upload_file", True, REMOTE_FILE)
        except Exception as e:
            record("upload_file", False, str(e))

        # Download file
        try:
            c.download_file(REMOTE_FILE, str(LOCAL_DOWNLOAD), 'A', force_raw=False)
            ok = LOCAL_DOWNLOAD.exists() and LOCAL_DOWNLOAD.stat().st_size > 0
            record("download_file", ok, f"{LOCAL_DOWNLOAD} {LOCAL_DOWNLOAD.stat().st_size if LOCAL_DOWNLOAD.exists() else 0} bytes")
        except Exception as e:
            record("download_file", False, str(e))

        # Delete file
        try:
            c.delete_file(REMOTE_FILE, 'A')
            record("delete_file", True, REMOTE_FILE)
        except Exception as e:
            record("delete_file", False, str(e))

        # Delete subdir (ignore if fails because not empty / already removed)
        try:
            c.delete_subdirectory(REMOTE_SUBDIR, 'A')
            record("delete_subdirectory(TST)", True)
        except Exception as e:
            record("delete_subdirectory(TST)", False, str(e))

        # Playback control
        try:
            c.pause()
            c.play()
            record("pause/play", True)
        except Exception as e:
            record("pause/play", False, str(e))

        # Real-time display
        try:
            c.real_time_display(f"API smoke {datetime.now():%H:%M:%S}")
            record("real_time_display", True)
        except Exception as e:
            record("real_time_display", False, str(e))

        # Restart schedule
        try:
            c.restart_schedule()
            record("restart_schedule", True)
        except Exception as e:
            record("restart_schedule", False, str(e))

        # Calendar clock
        try:
            now = datetime.now()
            c.set_calendar_clock(now.year, now.month, now.day, now.hour, now.minute, now.second)
            record("set_calendar_clock", True)
        except Exception as e:
            record("set_calendar_clock", False, str(e))

        # Explicitly release network (also done in close())
        try:
            c.release_network()
            record("release_network", True)
        except Exception as e:
            record("release_network", False, str(e))

except KeyboardInterrupt:
    pass
finally:
    # Local cleanup
    try:
        if LOCAL_UPLOAD.exists():
            LOCAL_UPLOAD.unlink()
        if LOCAL_DOWNLOAD.exists():
            LOCAL_DOWNLOAD.unlink()
        # Remove tmp dir
        try:
            TMP_DIR.rmdir()
        except OSError:
            # Directory not empty or busy; ignore
            pass
    except Exception:
        pass

# Summary and exit code
fails = [r for r in results if r[1] == 'FAIL']
print("\n===== SUMMARY =====")
for name, status, msg in results:
    print(f"{status:4} - {name} {('- ' + msg) if msg else ''}")
print(f"Total: {len(results)}; PASS: {len(results)-len(fails)}; FAIL: {len(fails)}")

sys.exit(0 if not fails else 1)
