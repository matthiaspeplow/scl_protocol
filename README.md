# SCL Protocol

A Python library for communicating with LyTech LED controllers via the SCL2008/SuperComm UDP protocol. This module provides complete protocol implementation including file operations, status queries, and automatic image conversion to XMP format.

## Features

- **Complete Protocol Implementation**: Full support for SCL2008 and SuperComm protocols
- **File Operations**: Upload, download, list files on controller storage (FLASH, SD card, RAM)
- **Status Monitoring**: Query controller status and disk free space
- **Image Conversion**: Automatic conversion of BMP, GIF, PNG monochrome images to XMP format
- **Robust Communication**: Built-in retry logic, timeout handling, and error recovery
- **Context Manager Support**: Clean resource management with `with` statements
- **Pure Python**: Minimal dependencies (only Pillow for image conversion)

## Installation

### From Source

```bash
cd scl_protocol
pip install -e .
```

Or using pip directly:

```bash
pip install .
```

The package uses modern Python packaging standards with `pyproject.toml` (PEP 517/660), ensuring compatibility with pip 25+ and avoiding deprecation warnings.

### Requirements

- Python 3.8 or higher
- Pillow >= 9.0.0 (for image conversion)
- setuptools >= 64.0.0 (automatically installed)

## Quick Start

```python
from scl_protocol import SCLController

# Connect to controller
with SCLController('192.168.1.100') as controller:
    # Check status
    status = controller.check_status()
    print(f"Connected: {status['connected']}")
    
    # List files on FLASH drive
    files = controller.list_files(driver='A')
    for file in files:
        print(f"{file['name']}: {file['size']} bytes")
    
    # Upload a file
    controller.upload_file('test.txt', driver='A', remote_path='test.txt')
    
    # Upload an image (automatically converts to XMP)
    controller.upload_file('logo.png', driver='A')
```

## API Reference

### SCLController Class

Main interface for controller communication.

#### Constructor

```python
SCLController(ip_address, port=5005, scl2008=True, timeout=5.0)
```

**Parameters:**
- `ip_address` (str): Controller IP address
- `port` (int): UDP port number (default: 5005)
- `scl2008` (bool): True for SCL2008 protocol, False for SuperComm (default: True)
- `timeout` (float): Socket timeout in seconds (default: 5.0)

#### Methods

##### `connect()`
Initialize UDP socket for communication.

##### `close()`
Close the UDP socket and release network resources.

##### `check_status() -> dict`
Read controller running status information.

**Returns:** Dictionary with detailed status information including:
- `connected` (bool): Connection status
- `total_programs` (int): Total program count
- `current_program` (int): Currently playing program number
- `program_driver` (str): Driver where current program is located ('A', 'B', or 'C')
- `sd_card_ready` (bool): SD card status
- `humidity` (int): Humidity from sensor (%)
- `temperature` (int): Temperature from DS18B20 (°C)
- `power_state` (int): Power supply state (0=Off, 1=On, 2=Auto)
- `power_mode` (int): Power mode setting
- `rtc` (dict): Real-time clock info with year, month, day, hour, minute, second, weekday
- `brightness` (int): LED brightness (0-30, 31=auto)
- `brightness_auto` (bool): True if brightness is in auto mode
- `program_index` (int): Which set of programs is playing
- `sw1_state` (int): State of SW1 port
- `sw2_state` (int): State of SW2 port

##### `get_play_status() -> dict`
Get current playlist playing status.

**Returns:** Dictionary with play status:
- `driver` (str): Driver where current PlayList.ly is ('A', 'B', or 'C')
- `subdirectory` (int): Subdirectory where current PlayList.ly is
- `playlist_item` (int): Current item in the PlayList.ly
- `area1_program` (int): Program displayed in area 1
- `area2_program` (int): Program displayed in area 2
- `area3_program` (int): Program displayed in area 3
- `area4_program` (int): Program displayed in area 4

##### `list_files(driver='A', subdirectory='') -> list`
List files on controller disk.

**Parameters:**
- `driver` (str): Driver letter ('A', 'B', or 'C')
- `subdirectory` (str): Subdirectory name (max 3 chars, empty for root)

**Returns:** List of dictionaries with file information:
- `name` (str): Filename
- `size` (int): File size in bytes
- `is_dir` (bool): True if directory
- `year`, `month`, `day`, `hour`, `minute`, `second`: File timestamp

##### `upload_file(local_path, driver='A', remote_path=None, pause_controller=False) -> bool`
Upload a file to the controller. Automatically converts BMP, GIF, or PNG images to XMP format.

**Parameters:**
- `local_path` (str): Path to local file
- `driver` (str): Destination driver ('A', 'B', or 'C')
- `remote_path` (str): Remote filename (defaults to local filename)
- `pause_controller` (bool): Whether to pause controller during upload

**Returns:** True if upload successful

##### `download_file(remote_path, local_path=None, driver='A', force_raw=False) -> bool`
Download a file from the controller. Automatically converts XMP files to BMP/GIF/PNG if local_path has those extensions.

**Parameters:**
- `remote_path` (str): Remote filename on controller (max 16 chars)
- `local_path` (str): Local destination path (defaults to remote filename)
- `driver` (str): Source driver ('A', 'B', or 'C')
- `force_raw` (bool): If True, always save as raw XMP without conversion

**Returns:** True if download successful

##### `download_directory(remote_dir, local_dir, driver='A', recursive=False) -> int`
Download all files from a directory on the controller.

**Parameters:**
- `remote_dir` (str): Remote directory name (max 3 chars, empty for root)
- `local_dir` (str): Local destination directory
- `driver` (str): Source driver ('A', 'B', or 'C')
- `recursive` (bool): Whether to download subdirectories (not implemented yet)

**Returns:** Number of files downloaded

##### `get_free_space(driver='A') -> int`
Get free space on controller disk.

**Parameters:**
- `driver` (str): Driver letter ('A', 'B', or 'C')

**Returns:** Free space in bytes

### Control Command Methods

##### `delete_file(remote_path, driver='A') -> bool`
Delete a file from the controller.

**Parameters:**
- `remote_path` (str): Remote file path to delete (max 16 chars)
- `driver` (str): Driver letter ('A', 'B', or 'C')

**Returns:** True if deletion successful

##### `pause() -> None`
Pause display playback.

##### `play() -> None`
Resume display playback.

##### `set_power_mode(mode) -> None`
Set LED screen power mode.

**Parameters:**
- `mode` (int): Power mode
  - `0`: Off
  - `1`: On
  - `2`: Auto

**Raises:** ValueError if mode is not 0, 1, or 2

##### `format_disk(driver) -> None`
Format a storage driver.

**Parameters:**
- `driver` (str): Driver letter ('A', 'B', or 'C')

**Warning:** This will ERASE ALL DATA on the driver!

##### `create_subdirectory(name, driver='A') -> None`
Create a subdirectory on the controller at the root level.

**Parameters:**
- `name` (str): Subdirectory name (max 3 characters, e.g., 'P00', 'FON')
- `driver` (str): Driver letter ('A', 'B', or 'C')

**Note:** Subdirectories can only be created at the root level. Nested subdirectories are not supported.

##### `delete_subdirectory(name, driver='A') -> None`
Delete a subdirectory from the controller at the root level.

**Parameters:**
- `name` (str): Subdirectory name (max 3 characters)
- `driver` (str): Driver letter ('A', 'B', or 'C')

**Note:** Directory must be empty before it can be deleted. Only root-level subdirectories can be deleted.

##### `set_calendar_clock(year, month, day, hour=0, minute=0, second=0) -> None`
Set controller's calendar and clock.

**Parameters:**
- `year` (int): Year (1980-2099)
- `month` (int): Month (1-12)
- `day` (int): Day (1-31)
- `hour` (int): Hour (0-23), default 0
- `minute` (int): Minute (0-59), default 0
- `second` (int): Second (0-59), default 0

##### `set_on_off_time(start_hour, start_minute, end_hour, end_minute, days_mask=0x7F) -> None`
Set display on/off time schedule.

**Parameters:**
- `start_hour` (int): Start hour (0-23)
- `start_minute` (int): Start minute (0-59)
- `end_hour` (int): End hour (0-23)
- `end_minute` (int): End minute (0-59)
- `days_mask` (int): Days bitmask (bit 0=Sunday, ..., bit 6=Saturday). Default 0x7F means all days

##### `real_time_display(text) -> None`
Send text for real-time display on LED screen.

**Parameters:**
- `text` (str): Text to display (max 256 characters, ASCII only)

##### `restart_schedule() -> None`
Restart the schedule list playback.

##### `reset_controller() -> None`
Reset (reboot) the controller.

**Warning:** This will reboot the controller!

##### `release_network() -> None`
Release network communication to allow other clients to connect.

**Note:** Should be called after completing a communication process. The controller automatically releases network on `close()`, so this is typically only needed for long-running sessions.

### Image Conversion Functions

##### `convert_to_xmp(image_path, output_path=None, xmp_type=1) -> tuple`
Convert a monochrome or grayscale image (BMP, GIF, PNG) to XMP format.

**Parameters:**
- `image_path` (str): Path to source image file
- `output_path` (str, optional): Destination path for XMP file. If None, creates a temporary file.
- `xmp_type` (int, optional): XMP format type. Default is 1.
  - `1`: Type 1 (4-color grayscale, 2 bits per pixel) - Better compatibility
  - `2`: Type 2 (monochrome, 1 bit per pixel)

**Returns:** Tuple of (output_path, is_temporary)

##### `needs_conversion(filename) -> bool`
Check if a file needs conversion before upload.

**Parameters:**
- `filename` (str): Path or filename to check

**Returns:** True if file should be converted to XMP before upload

### Exceptions

All exceptions inherit from `SCLProtocolError`.

- **`SCLProtocolError`**: Base exception for all protocol errors
- **`SCLControllerError`**: Controller communication errors
- **`SCLConnectionError`**: Connection-specific errors
- **`SCLTimeoutError`**: Timeout errors
- **`ImageConversionError`**: Image conversion errors

### Constants

- **`DRIVER_FLASH`** (0): FLASH memory (Driver A)
- **`DRIVER_SD_CARD`** (1): SD card (Driver B)
- **`DRIVER_RAM`** (2): RAM (Driver C)
- **`DRIVER_NAMES`**: Dictionary mapping driver letters to numbers and vice versa
- **`DEFAULT_UDP_PORT`** (5005): Default UDP port for controller communication

## Usage Examples

### Check Controller Status

```python
from scl_protocol import SCLController, SCLControllerError

try:
    with SCLController('192.168.1.100') as controller:
        status = controller.check_status()
        print(f"Controller Status: {status['connected']}")
        
        # Get free space on all drives
        for driver in ['A', 'B', 'C']:
            try:
                free = controller.get_free_space(driver)
                print(f"Driver {driver}: {free / (1024*1024):.2f} MB free")
            except SCLControllerError:
                print(f"Driver {driver}: Not available")
except SCLControllerError as e:
    print(f"Error: {e}")
```

### List and Download Files

```python
from scl_protocol import SCLController

with SCLController('192.168.1.100') as controller:
    # List files on FLASH drive
    files = controller.list_files(driver='A')
    
    for file in files:
        if not file['is_dir']:
            print(f"File: {file['name']}, Size: {file['size']} bytes")
    
    # Download a specific file
    controller.download_file('config.txt', 'downloaded_config.txt', driver='A')
    
    # Download entire directory
    count = controller.download_directory('P01', './downloads', driver='A')
    print(f"Downloaded {count} files")
```

### Upload Files with Image Conversion

```python
from scl_protocol import SCLController, needs_conversion

with SCLController('192.168.1.100') as controller:
    # Upload a regular text file
    controller.upload_file('playlist.txt', driver='A')
    
    # Upload an image - automatically converts to XMP
    image_file = 'logo.png'
    if needs_conversion(image_file):
        print(f"{image_file} will be converted to XMP format")
    
    controller.upload_file(image_file, driver='A', remote_path='logo.xmp')
    
    # Upload with controller pause (recommended for large files)
    controller.upload_file('large_file.dat', driver='A', pause_controller=True)
```

### Offline Image Conversion

```python
from scl_protocol import convert_to_xmp, ImageConversionError

try:
    # Convert image to XMP format (Type 1: 4-color grayscale, default)
    output_path, is_temp = convert_to_xmp('input.png', 'output.xmp')
    print(f"Converted to: {output_path}")
    
    # Convert to Type 2 (monochrome) instead
    output_path, is_temp = convert_to_xmp('input.png', 'output_mono.xmp', xmp_type=2)
    print(f"Converted to monochrome: {output_path}")
    
    # Temporary file will be cleaned up automatically if is_temp is True
except ImageConversionError as e:
    print(f"Conversion failed: {e}")
```

### Controller Control Operations

```python
from scl_protocol import SCLController

with SCLController('192.168.1.100') as controller:
    # Playback control
    controller.pause()  # Pause display
    controller.play()   # Resume display
    
    # Get current play status
    status = controller.get_play_status()
    print(f"Playing from driver {status['driver']}, item {status['playlist_item']}")
    
    # Power management
    controller.set_power_mode(1)  # Turn on
    controller.set_power_mode(2)  # Auto mode
    
    # Set schedule: Display on from 8:00 to 18:00, all days
    controller.set_on_off_time(8, 0, 18, 0, days_mask=0x7F)
    
    # Set controller clock
    from datetime import datetime
    now = datetime.now()
    controller.set_calendar_clock(now.year, now.month, now.day, 
                                  now.hour, now.minute, now.second)
    
    # Display real-time text
    controller.real_time_display("Hello LED!")
    
    # Restart schedule playback
    controller.restart_schedule()
```

### Directory and File Management

```python
from scl_protocol import SCLController

with SCLController('192.168.1.100') as controller:
    # Create a new subdirectory
    controller.create_subdirectory('P99', driver='A')
    
    # Upload files to subdirectory
    controller.upload_file('logo.png', driver='A', remote_path='P99/LOGO.XMP')
    
    # List files in subdirectory
    files = controller.list_files(driver='A', subdirectory='P99')
    print(f"Found {len(files)} files in P99")
    
    # Delete a specific file
    controller.delete_file('P99/LOGO.XMP', driver='A')
    
    # Delete subdirectory (must be empty)
    controller.delete_subdirectory('P99', driver='A')
    
    # Format disk (WARNING: erases all data!)
    # controller.format_disk('C')  # Only format RAM drive for safety
```

### Error Handling

```python
from scl_protocol import (
    SCLController,
    SCLConnectionError,
    SCLTimeoutError,
    SCLControllerError
)

try:
    with SCLController('192.168.1.100', timeout=10.0) as controller:
        controller.upload_file('test.txt', driver='A')
except SCLConnectionError as e:
    print(f"Connection failed: {e}")
except SCLTimeoutError as e:
    print(f"Operation timed out: {e}")
except SCLControllerError as e:
    print(f"Controller error: {e}")
```

## Interactive Test Script

The package includes a comprehensive interactive test script for testing all functionality:

```bash
python tests/interactive_test.py
```

The script provides a menu-driven interface to:
1. Setup connection parameters
2. Test connection to controller
3. Check controller status
4. List files on controller
5. Upload files (with automatic image conversion)
6. Download files
7. Download entire directories
8. Get disk free space
9. Test image conversion offline
0. Exit

The interactive test script is useful for:
- Testing connection to a new controller
- Exploring controller file system
- Testing image conversion without uploading
- Learning the API through practical examples

## Protocol Details

### UDP Communication

The SCL protocol uses UDP for communication:
- **Packet Structure**: Leading code (4B) + Packet number (4B) + Length (2B) + Reserved (2B) + Basic data
- **Little-Endian**: All multi-byte values use little-endian encoding
- **Response Port**: Controller responds on the same port as the request
- **Packet Numbering**: Sequential packet numbers starting from 1
- **Buffer Management**: 2MB communication buffer for file transfers
- **Maximum Data Size**: 1024 bytes per packet

### XMP Image Format

XMP is a proprietary bitmap format used by LyTech LED controllers. The library automatically converts BMP, GIF, and PNG images to XMP format during upload.

**Supported Formats:**
- **Type 1 (4-color grayscale)** - Default, best compatibility
- **Type 2 (monochrome)** - Smaller file size

**Basic Usage:**
```python
# Default Type 1 conversion
controller.upload_file('image.png', driver='A')

# Explicit Type 2 conversion
from scl_protocol import convert_to_xmp
convert_to_xmp('image.png', 'output.xmp', xmp_type=2)
```

For detailed XMP format specifications, pixel storage order, and implementation details, see [XMP_FORMAT_NOTES.md](XMP_FORMAT_NOTES.md).

### Supported Commands

The library implements these protocol commands:

- `0x00000000`: Send data to buffer
- `0x00000001`: Retrieve data from buffer
- `0x00000002`: Save buffer to file
- `0x00000003`: Load file to buffer
- `0x00000004`: Delete file
- `0x00000005`: Get disk free space
- `0x00000006`: Download directory listing
- `0x00000007`: Format disk
- `0x00000009`: Set calendar/clock
- `0x0000000A`: Pause/play control
- `0x0000000B`: Set on/off time
- `0x0000000C`: Setup power mode
- `0x0000000D`: Create subdirectory
- `0x0000000E`: Delete subdirectory
- `0x00000084`: Read running info (status)
- `0x000055AA`: Reset controller / Release network

### File Naming Conventions

- Maximum filename length: 16 characters (including subdirectory prefix)
- Subdirectory names: Maximum 3 characters (e.g., P00, P01, P99)
- **Path separator**: Use forward slash `/` in API calls (e.g., `P00/FILE.TXT`)
  - The library automatically converts to backslash `\` for DOS-style controller paths
- Format: `SUB/FILE.EXT` where SUB is ≤3 chars, FILE.EXT follows 8.3 format
- Valid examples: `CONFIG.LY`, `P01/TEST.TXT`, `SHOW.DAT`
- **Important**: Controller expects DOS-style paths internally, but you should use Unix-style `/` in your code

#### Subdirectory Structure Limitations

**Root Level Only**: Subdirectories can only be created at the root level of each driver. Nested subdirectories (subdirectories within subdirectories) are NOT supported by the controller hardware.

```
Supported Structure:
Driver A:/
  ├── P00/         ✓ Root-level subdirectory
  │   └── file.txt ✓ File in subdirectory
  ├── P01/         ✓ Root-level subdirectory
  └── file.txt     ✓ Root-level file

NOT Supported:
Driver A:/
  └── P00/
      └── NESTED/  ✗ Nested subdirectory (NOT SUPPORTED)
```

**File Path Examples**:
- `file.txt` - ✓ Root level
- `P00/file.txt` - ✓ One level deep (subdirectory)
- `P00/SUB/file.txt` - ✗ Two levels deep (NOT SUPPORTED)

**Subdirectory Operations**:
- `create_subdirectory()` - Creates root-level subdirectories only
- `delete_subdirectory()` - Deletes root-level subdirectories only (must be empty)
- Both operations are limited to 3-character names

This is a hardware/firmware limitation of the LyTech LED controller, not a limitation of the scl_protocol library.

### Driver Mapping

- **Driver A (DRIVER_FLASH)**: FLASH memory - Internal storage
- **Driver B (DRIVER_SD_CARD)**: SD card - External storage
- **Driver C (DRIVER_RAM)**: RAM - Temporary storage (lost on power off)

## Troubleshooting

### Connection Issues

**Problem**: Timeout errors or connection failures

**Solutions**:
1. Verify controller IP address is correct
2. Check network connectivity: `ping <controller_ip>`
3. Ensure controller is powered on and network cable connected
4. Try increasing timeout: `SCLController(ip, timeout=10.0)`
5. Check firewall settings (UDP port must be open)
6. Verify you're on the same network segment

### Protocol Errors

**Problem**: Protocol errors or invalid responses

**Solutions**:
1. Verify correct protocol version: `scl2008=True` for SCL2008, `scl2008=False` for SuperComm
2. Check controller firmware compatibility
3. Ensure no other software is communicating with the controller simultaneously
4. Try power-cycling the controller

### Upload Failures

**Problem**: File upload fails or times out

**Solutions**:
1. Check file size (must be < 2MB due to controller buffer limitation)
2. Verify sufficient free space: `controller.get_free_space(driver)`
3. Try using pause mode: `upload_file(..., pause_controller=True)`
4. Verify remote filename length (max 16 chars including subdirectory)
5. Check that the destination driver is writable (RAM may be disabled)

### Image Conversion Errors

**Problem**: Image conversion fails

**Solutions**:
1. Ensure Pillow is installed: `pip install Pillow`
2. Verify image file is valid and not corrupted
3. Check that image is in supported format (BMP, GIF, or PNG)
4. Very large images may exceed controller capabilities - try resizing first
5. Ensure image is monochrome or can be converted to monochrome

## Development

### Project Structure

```
scl_protocol/
├── scl_protocol/
│   ├── __init__.py         # Public API exports
│   ├── constants.py        # Protocol constants and command codes
│   ├── protocol.py         # Packet building and parsing
│   ├── controller.py       # Main controller class
│   ├── image_converter.py  # XMP image conversion
│   └── exceptions.py       # Exception hierarchy
├── tests/
│   └── interactive_test.py # Interactive testing script
├── pyproject.toml          # Modern build configuration (PEP 517/660)
├── setup.py                # Legacy package configuration (optional)
├── requirements.txt        # Dependencies
└── README.md              # This file
```

### Testing

Run the interactive test script:

```bash
python tests/interactive_test.py
```

For automated testing (requires a controller or mock):

```python
from scl_protocol import SCLController

# Test basic import
assert SCLController is not None

# Test connection (requires actual controller)
with SCLController('192.168.1.100') as controller:
    status = controller.check_status()
    assert status['connected'] == True
```

## License

MIT License - see LICENSE file for details

## Author

Matthias Peplow

## Acknowledgments

Based on the SCL/SuperComm protocol specification by LyTech for LED controller communication.

## Related Documentation

For detailed protocol information, refer to:
- SCL Protocol specification document
- SCL2008 Protocol packet examples
- LyTech controller programming manual

## Version History

### 0.9.0 (2025-11-25)
- Initial release
- Complete SCL2008 and SuperComm protocol implementation
- File upload/download with automatic image conversion
- Status monitoring and disk space queries
- Robust error handling and retry logic
- Interactive test script
- Comprehensive documentation
- **Critical fix**: DOS-style path separator handling for subdirectories
- **Fix**: Correct CMD_LOAD_FILE_TO_BUFFER parameter structure (two reservation DWORDs)
- **Fix**: 100ms delay after loading file to buffer for controller processing
- Modern packaging with pyproject.toml (PEP 517/660 compliant)
