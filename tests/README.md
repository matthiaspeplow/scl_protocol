# Tests

This directory contains test scripts for the scl_protocol library.

## Test Scripts

### interactive_test.py
Interactive test script with a menu-driven interface for testing all controller functionality.

**Usage:**
```bash
python tests/interactive_test.py
```

**Features:**
- Connection testing
- Status queries
- File upload/download
- Directory operations
- Image conversion testing
- Disk space queries

**Requirements:**
- Access to a LyTech LED controller on the network
- Controller IP address

### test_completeness.py
Validation script that verifies all SCL protocol commands have corresponding methods implemented.

**Usage:**
```bash
python tests/test_completeness.py
```

**Purpose:**
- Verifies all command codes are covered
- Lists all public methods
- Categorizes methods by functionality
- Reports any missing implementations

**Exit Codes:**
- `0` - All methods implemented
- `1` - Missing methods detected

### run_api_smoke.py
Automated smoke test that exercises all major public methods against a live controller.

**Usage:**
```bash
python tests/run_api_smoke.py <controller_ip>
# Example:
python tests/run_api_smoke.py 172.31.16.25
```

**Tests Performed:**
- Connection and network release
- Status queries (check_status, get_play_status, get_free_space, list_files)
- File operations (create_subdirectory, upload_file, download_file, delete_file, delete_subdirectory)
- Control commands (pause, play, real_time_display, restart_schedule, set_calendar_clock)

**NOT Tested (destructive/persistent):**
- format_disk (erases data)
- reset_controller (reboots controller)
- set_on_off_time, set_power_mode (persistent settings)

**Exit Codes:**
- `0` - All tests passed
- `1` - One or more tests failed
- `2` - Missing controller IP argument

**Cleanup:** Automatically removes temporary files and directories created during testing.

## Running Tests

### Interactive Testing
For manual testing with an actual controller:
```bash
cd scl_protocol
python tests/interactive_test.py
```

### Completeness Check
To verify the implementation:
```bash
cd scl_protocol
python tests/test_completeness.py
```

## Test Output
Test scripts may create temporary files or directories during execution. These are not tracked by git and should be cleaned up automatically.
