# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.1.1] - 2024-12-08

### Fixed
- **Critical**: Packet counter synchronization issues in `send_command()` method
  - Packet not rebuilt on retry - packet number was updated but packet still contained old number
  - Insufficient socket buffer flushing before resync - stale packets could cause cascading failures
  - Improved resync logic to properly align with controller's packet counter
  - Added socket buffer flush before retry to prevent stale packet issues

### Changed
- Replaced `print()` with proper `logging` module for packet counter warnings
- Added debug-level logging for packet counter state transitions
- Enhanced error messages with command code and retry attempt information
- Moved packet building inside retry loop to ensure fresh packet on each attempt

### Added
- Comprehensive documentation of packet counter fix in PACKET_COUNTER_FIX.md
- Debug logging showing packet number transitions (enable with `logging.DEBUG`)

## [0.2.0] - 2024-11-27

### Added
- Type 1 XMP format support (4-color grayscale, 2 bits per pixel, 26-byte header)
- `xmp_type` parameter to `convert_to_xmp()` function (1=grayscale, 2=monochrome)
- Type 1 is now the default format for better controller compatibility
- XMP type selection in interactive test script (option 9)

### Changed
- **Breaking**: Default XMP conversion now produces Type 1 (grayscale) instead of Type 2 (monochrome)
- Updated documentation to explain both XMP format types
- Image converter now supports grayscale images with 4 intensity levels (black, dark gray, light gray, white)

### Fixed
- XMP format compatibility - now matches controller's native Type 1 format
- File sizes now match downloaded XMP files from controller (Type 1: ~2x size of Type 2)

## [0.1.0] - 2024-11-24

### Added
- Complete implementation of SCL2008 and SuperComm protocols
- `SCLController` class with full controller communication
- File operations: upload, download, list files, get free space
- Automatic BMP/GIF/PNG to XMP image conversion using Pillow
- Context manager support for clean resource management
- Comprehensive exception hierarchy (SCLProtocolError, SCLControllerError, etc.)
- Interactive test script with menu-driven interface
- Debug test script for troubleshooting downloads
- Modern packaging with pyproject.toml (PEP 517/660 compliant)
- Comprehensive documentation and usage examples

### Fixed
- **Critical**: DOS-style path separator handling - controller expects backslash `\` not forward slash `/` for subdirectories
- **Critical**: CMD_LOAD_FILE_TO_BUFFER parameter structure - must include two reservation DWORDs (PA2=0 and DWORD in PA3)
- Added 100ms delay after CMD_LOAD_FILE_TO_BUFFER to give controller time to load file from disk to buffer
- Proper error handling with specific exception types (SCLConnectionError, SCLTimeoutError)
- Socket buffer flushing to prevent stale packet issues
- Packet number tracking with retry logic

### Technical Details
- UDP packet structure: leading code (4B) + packet# (4B) + length (2B) + reserved (2B) + basic data
- Little-endian encoding throughout
- 2MB communication buffer with chunked transfers (max 1024 bytes per packet)
- DOS datetime format for file timestamps
- Directory entry parsing (32-byte structures)

### Known Limitations
- Recursive directory download not yet implemented
- Maximum file size: 2MB (controller buffer limitation)
- Maximum filename length: 16 characters including subdirectory
- Subdirectory names limited to 3 characters

[0.1.0]: https://github.com/yourusername/scl-protocol/releases/tag/v0.1.0
