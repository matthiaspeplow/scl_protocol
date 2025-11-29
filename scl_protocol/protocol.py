"""
Protocol module for building and parsing SCL protocol packets.
Handles binary packet construction and response parsing with proper endianness.
"""

import struct
from typing import Tuple, Optional
from .constants import (
    LEADING_CODE_PC_SCL2008,
    LEADING_CODE_CONTROLLER_SCL2008,
    LEADING_CODE_PC_SUPERCOMM,
    LEADING_CODE_CONTROLLER_SUPERCOMM,
    UDP_HEADER_SIZE,
)
from .exceptions import SCLProtocolError


def build_udp_packet(packet_num: int, basic_data: bytes, scl2008: bool = True) -> bytes:
    """
    Build a complete UDP packet for SCL protocol.
    
    Args:
        packet_num: Packet sequence number (starts at 1)
        basic_data: Basic data packet payload
        scl2008: True for SCL2008 protocol, False for SuperComm
    
    Returns:
        Complete UDP packet as bytes
    
    Raises:
        SCLProtocolError: If packet construction fails
    """
    if packet_num < 0:
        raise SCLProtocolError("Packet number must be >= 0")
    
    if len(basic_data) > 1036:
        raise SCLProtocolError(f"Basic data packet too large: {len(basic_data)} bytes (max 1036)")
    
    # Select leading code based on protocol version
    leading_code = LEADING_CODE_PC_SCL2008 if scl2008 else LEADING_CODE_PC_SUPERCOMM
    
    # Calculate packet length (basic data + 12 header bytes)
    packet_length = len(basic_data) + UDP_HEADER_SIZE
    
    # Build packet: leading(4) + packet#(4) + length(2) + reserved(2) + basic_data
    packet = struct.pack(
        '<4sIHH',
        leading_code,      # 4 bytes leading code
        packet_num,        # 4 bytes packet number (DWORD, little-endian)
        packet_length,     # 2 bytes packet length (WORD, little-endian)
        0x0000            # 2 bytes reserved (WORD)
    )
    packet += basic_data
    
    return packet


def build_basic_data_packet(command: int, param1: int = 0, param2: int = 0, 
                           param3: Optional[bytes] = None) -> bytes:
    """
    Build a basic data packet with command and parameters.
    
    Args:
        command: Command code (DWORD)
        param1: Parameter 1 (DWORD)
        param2: Parameter 2 (DWORD)
        param3: Optional parameter 3 (variable bytes)
    
    Returns:
        Basic data packet as bytes
    """
    # Pack command and first two parameters (all DWORDs, little-endian)
    basic_data = struct.pack('<III', command, param1, param2)
    
    # Append optional parameter 3
    if param3 is not None:
        basic_data += param3
    
    return basic_data


def parse_response(data: bytes, scl2008: bool = True) -> Tuple[int, int, int, int, Optional[bytes]]:
    """
    Parse a response packet from the controller.
    
    Args:
        data: Raw response packet bytes
        scl2008: True for SCL2008 protocol, False for SuperComm
    
    Returns:
        Tuple of (packet_num, command, param1, param2, param3)
        where param3 is None if not present
    
    Raises:
        SCLProtocolError: If packet parsing fails
    """
    if len(data) < UDP_HEADER_SIZE + 12:  # Minimum size: header + command + PA1 + PA2
        raise SCLProtocolError(f"Response packet too short: {len(data)} bytes")
    
    # Select expected leading code based on protocol version
    expected_leading = LEADING_CODE_CONTROLLER_SCL2008 if scl2008 else LEADING_CODE_CONTROLLER_SUPERCOMM
    
    # Parse UDP header
    leading_code = data[0:4]
    if leading_code != expected_leading:
        raise SCLProtocolError(
            f"Invalid leading code: {leading_code.hex()} "
            f"(expected {expected_leading.hex()})"
        )
    
    # Unpack header: packet#(4) + length(2) + reserved(2)
    packet_num, packet_length, _ = struct.unpack('<IHH', data[4:12])
    
    # Validate packet length
    if packet_length != len(data):
        raise SCLProtocolError(
            f"Packet length mismatch: header says {packet_length}, "
            f"actual {len(data)}"
        )
    
    # Parse basic data packet: command(4) + PA1(4) + PA2(4)
    basic_data = data[12:]
    if len(basic_data) < 12:
        raise SCLProtocolError(f"Basic data packet too short: {len(basic_data)} bytes")
    
    command, param1, param2 = struct.unpack('<III', basic_data[0:12])
    
    # Extract optional PA3
    param3 = basic_data[12:] if len(basic_data) > 12 else None
    
    return packet_num, command, param1, param2, param3


def pack_filename(filename: str, buffer_size: int = 32) -> bytes:
    """
    Pack a filename into a fixed-size buffer with null termination.
    
    Args:
        filename: Filename string (max 16 characters including path)
        buffer_size: Size of output buffer (default 32)
    
    Returns:
        Null-padded filename bytes
    
    Raises:
        SCLProtocolError: If filename is too long
    """
    encoded = filename.encode('ascii')
    if len(encoded) >= buffer_size:
        raise SCLProtocolError(
            f"Filename too long: {len(encoded)} bytes (max {buffer_size - 1})"
        )
    
    # Null-terminate and pad to buffer size
    return encoded + b'\x00' * (buffer_size - len(encoded))


def parse_filename(data: bytes) -> str:
    """
    Parse a null-terminated filename from bytes.
    
    Args:
        data: Filename bytes
    
    Returns:
        Decoded filename string
    """
    # Find null terminator
    null_pos = data.find(b'\x00')
    if null_pos >= 0:
        data = data[:null_pos]
    
    return data.decode('ascii', errors='replace').strip()


def pack_dos_datetime(year: int, month: int, day: int, 
                      hour: int = 0, minute: int = 0, second: int = 0) -> Tuple[int, int]:
    """
    Pack date and time into DOS format (WORD each).
    
    Args:
        year: Year (1980-2099)
        month: Month (1-12)
        day: Day (1-31)
        hour: Hour (0-23)
        minute: Minute (0-59)
        second: Second (0-59)
    
    Returns:
        Tuple of (time_word, date_word)
    """
    # Time format: bits 15-11: hour, 10-5: minute, 4-0: second/2
    time_word = ((hour & 0x1F) << 11) | ((minute & 0x3F) << 5) | ((second // 2) & 0x1F)
    
    # Date format: bits 15-9: year-1980, 8-5: month, 4-0: day
    date_word = (((year - 1980) & 0x7F) << 9) | ((month & 0x0F) << 5) | (day & 0x1F)
    
    return time_word, date_word


def parse_dos_datetime(time_word: int, date_word: int) -> Tuple[int, int, int, int, int, int]:
    """
    Parse DOS format date and time.
    
    Args:
        time_word: DOS time (WORD)
        date_word: DOS date (WORD)
    
    Returns:
        Tuple of (year, month, day, hour, minute, second)
    """
    hour = (time_word >> 11) & 0x1F
    minute = (time_word >> 5) & 0x3F
    second = (time_word & 0x1F) * 2
    
    year = ((date_word >> 9) & 0x7F) + 1980
    month = (date_word >> 5) & 0x0F
    day = date_word & 0x1F
    
    return year, month, day, hour, minute, second


def parse_directory_entry(data: bytes) -> dict:
    """
    Parse a 32-byte directory entry.
    
    Args:
        data: 32-byte directory entry
    
    Returns:
        Dictionary with keys: name, extension, is_dir, size, date, time
    
    Raises:
        SCLProtocolError: If entry is invalid
    """
    if len(data) != 32:
        raise SCLProtocolError(f"Directory entry must be 32 bytes, got {len(data)}")
    
    # Parse filename (bytes 0-7) and extension (bytes 8-10)
    filename = data[0:8].decode('ascii', errors='replace').strip()
    extension = data[8:11].decode('ascii', errors='replace').strip()
    
    # Build full name
    if extension:
        name = f"{filename}.{extension}"
    else:
        name = filename
    
    # Parse attributes (byte 11)
    attributes = data[11]
    is_dir = (attributes == 0x10)
    
    # Parse time (bytes 22-23) and date (bytes 24-25)
    time_word = struct.unpack('<H', data[22:24])[0]
    date_word = struct.unpack('<H', data[24:26])[0]
    year, month, day, hour, minute, second = parse_dos_datetime(time_word, date_word)
    
    # Parse file size (bytes 28-31)
    size = struct.unpack('<I', data[28:32])[0]
    
    return {
        'name': name,
        'extension': extension,
        'is_dir': is_dir,
        'size': size,
        'year': year,
        'month': month,
        'day': day,
        'hour': hour,
        'minute': minute,
        'second': second,
    }
