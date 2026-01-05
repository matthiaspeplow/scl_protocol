# SCL Protocol Scripts

Utility scripts for testing and managing LED controllers using the SCL protocol library.

## Setup Scripts

### create_test_directory.py

Creates a test directory (P99) on the LED controller for safe testing without affecting production files.

**Usage:**
```bash
# Create P99 test directory with defaults
python3 scripts/create_test_directory.py

# Specify controller IP
python3 scripts/create_test_directory.py --ip 172.31.16.25

# Create different test directory
python3 scripts/create_test_directory.py --name P98

# Full options
python3 scripts/create_test_directory.py --ip 172.31.16.25 --port 1024 --name P99 --driver A
```

**Why you need this:**
- Prevents accidentally overwriting production files in P00
- Provides isolated environment for testing uploads
- Can be safely cleared without affecting production

**When to run:**
- Before running any upload tests
- After controller reset/format
- When setting up new test environment

## Test Scripts

### Interactive Test (from main directory)
```bash
cd /Users/matthias.peplow/Development/scl_protocol
python3 -m scl_protocol.test_interactive
```

Full interactive menu for testing all controller functions.

## Integration with sf-led_anzeige

The scl_protocol library is used by the sf-led_anzeige application as an editable install.

**Test connection from sf-led_anzeige:**
```bash
cd /Users/matthias.peplow/Development/sf-led_anzeige
python3 scripts/test_connection.py
```

**Test uploads (uses production P00 by default):**
```bash
cd /Users/matthias.peplow/Development/sf-led_anzeige

# Test single file upload
python3 -c "
from pathlib import Path
from led_display.uploader import LEDUploader
uploader = LEDUploader()
uploader.upload_file(Path('output/Black.png'), force=True)
"
```

**⚠️ WARNING:** The sf-led_anzeige uploader uses P00 (production) by default.  
For testing, use the scl_protocol library directly with P99:

```python
from scl_protocol import SCLController

with SCLController('172.31.16.25', port=1024) as controller:
    # Upload to test directory P99
    controller.upload_file('output/test.png', 'A', 'P99/test.png')
```

## Common Tasks

### Create Test Directory
```bash
python3 scripts/create_test_directory.py
```

### Check Controller Status
```python
from scl_protocol import SCLController

with SCLController('172.31.16.25') as controller:
    status = controller.check_status()
    print(f"Programs: {status['total_programs']}")
    print(f"Brightness: {status['brightness']}")
```

### List Files
```python
from scl_protocol import SCLController

with SCLController('172.31.16.25') as controller:
    # List production directory
    files = controller.list_files('A', 'P00')
    
    # List test directory
    test_files = controller.list_files('A', 'P99')
```

### Safe Testing Pattern
```python
from scl_protocol import SCLController

# Always use P99 for testing!
TEST_DIR = 'P99'

with SCLController('172.31.16.25') as controller:
    # Upload test file
    controller.upload_file('test.png', 'A', f'{TEST_DIR}/test.png')
    
    # Verify
    files = controller.list_files('A', TEST_DIR)
    print(f"Files in {TEST_DIR}: {len(files)}")
    
    # Clean up (optional)
    # controller.delete_file(f'{TEST_DIR}/test.png', 'A')
```

## Directory Structure on Controller

```
A:/ (FLASH memory)
├── P00/          ← PRODUCTION (do not test here!)
│   ├── AKQA.PNG
│   ├── BURSON.PNG
│   ├── CURRENT.PNG
│   └── ...
└── P99/          ← TEST DIRECTORY (safe for testing)
    └── (test files)

B:/ (SD card)
C:/ (RAM)
```

## Troubleshooting

### "Directory P99 not found"
Run the setup script:
```bash
python3 scripts/create_test_directory.py
```

### "Timeout waiting for response"
- Check controller is powered on
- Verify network connectivity: `ping 172.31.16.25`
- Ensure no other process is locking the controller
- Try releasing the lock:
  ```python
  from scl_protocol import SCLController
  with SCLController('172.31.16.25') as c:
      c.release_network()
  ```

### "Packet counter out of sync"
This should auto-recover with the v0.1.1 fix. If you see this warning repeatedly:
- Check network stability
- Verify controller firmware is up to date
- Review logs for patterns
- File an issue with debug logs

## Related Documentation

- [PACKET_COUNTER_FIX.md](../PACKET_COUNTER_FIX.md) - Details on packet counter synchronization fix
- [TEST_RESULTS.md](../TEST_RESULTS.md) - Comprehensive test results
- [README.md](../README.md) - Main library documentation
- [CHANGELOG.md](../CHANGELOG.md) - Version history

## Support

For issues or questions:
- Check [TEST_RESULTS.md](../TEST_RESULTS.md) for known issues
- Review [CHANGELOG.md](../CHANGELOG.md) for recent fixes
- Contact IT team at ber-admins@s-f.com
