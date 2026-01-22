"""
Controller module for communicating with LyTec SCL2008 or SuperCom LED controllers.
Implements high-level operations: status check, file listing, and file upload and image conversion from bmp,png and jpg to xmp and vice versa.
Tested with SCL2008 only
"""

import logging
import socket
import struct
import time
from pathlib import Path
from typing import List, Dict, Optional, Tuple
from datetime import datetime

logger = logging.getLogger(__name__)

from .image_converter import convert_to_xmp, needs_conversion
from .protocol import (
    build_udp_packet,
    build_basic_data_packet,
    parse_response,
    pack_filename,
    pack_dos_datetime,
    parse_directory_entry,
)
from .exceptions import (
    SCLProtocolError,
    SCLControllerError,
    SCLConnectionError,
    SCLTimeoutError,
    ImageConversionError,
)
from .constants import (
    CMD_SEND_DATA_TO_BUFFER,
    CMD_RETRIEVE_DATA_FROM_BUFFER,
    CMD_SAVE_BUFFER_TO_FILE,
    CMD_LOAD_FILE_TO_BUFFER,
    CMD_DOWNLOAD_DIRECTORY,
    CMD_READ_RUNNING_INFO,
    CMD_PLAY_STATUS,
    CMD_PAUSE_PLAY,
    CMD_RELEASE_NET_COMM,
    ERROR_CODE,
    SUCCESS_CODE,
    COMM_BUFFER_SIZE,
    MAX_PACKET_DATA_SIZE,
    MAX_FILENAME_LENGTH,
    MAX_SUBDIRECTORY_LENGTH,
    DRIVER_NAMES,
    DRIVER_FLASH,
    PAUSE_MODE,
    PLAY_MODE,
    DEFAULT_TIMEOUT,
    DEFAULT_UDP_PORT,
)


class SCLController:
    """
    Main interface for communicating with LyTech LED controllers.
    """
    
    def __init__(self, ip_address: str, port: int = DEFAULT_UDP_PORT, 
                 scl2008: bool = True, timeout: float = DEFAULT_TIMEOUT):
        """
        Initialize controller connection.
        
        Args:
            ip_address: Controller IP address
            port: UDP port (default from constants)
            scl2008: True for SCL2008 protocol, False for SuperComm
            timeout: Socket timeout in seconds
        """
        self.ip_address = ip_address
        self.port = port
        self.scl2008 = scl2008
        self.timeout = timeout
        self.socket = None
        self.packet_num = 0
        
    def connect(self):
        """
        Initialize UDP socket for communication.
        
        Raises:
            SCLControllerError: If socket creation fails
        """
        try:
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            self.socket.settimeout(self.timeout)
            # Start packet numbering from 0 so first increment makes it 1
            # Controller uses 1-based packet numbering
            self.packet_num = 0
            # Flush any stale packets from socket buffer
            self._flush_socket_buffer()
        except socket.error as e:
            raise SCLConnectionError(f"Failed to create socket: {e}")
    
    def close(self):
        """Close the UDP socket."""
        if self.socket:
            try:
                # Release network communication before closing (non-blocking)
                self._send_release_command()
            except Exception:
                # Best effort - don't fail close if release command fails
                pass
            finally:
                self.socket.close()
                self.socket = None
    
    def __enter__(self):
        """Context manager entry."""
        self.connect()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()
    
    def _flush_socket_buffer(self):
        """Flush any stale packets from the socket buffer."""
        if not self.socket:
            return
        
        # Set socket to non-blocking temporarily
        self.socket.setblocking(False)
        try:
            # Read and discard any pending packets
            while True:
                try:
                    self.socket.recvfrom(4096)
                except socket.error:
                    break
        finally:
            # Restore blocking mode with timeout
            self.socket.setblocking(True)
            self.socket.settimeout(self.timeout)
    
    def _send_release_command(self):
        """Send release network communication command without waiting for response."""
        if not self.socket:
            return
        
        # Increment packet number
        self.packet_num += 1
        
        # Build and send release command packet (PA1=2 for release net communication)
        from .protocol import build_basic_data_packet, build_udp_packet
        basic_data = build_basic_data_packet(CMD_RELEASE_NET_COMM, 2, 0, None)
        packet = build_udp_packet(self.packet_num, basic_data, self.scl2008)
        
        try:
            self.socket.sendto(packet, (self.ip_address, self.port))
            # Don't wait for response - best effort only
        except Exception:
            pass
    
    def release_network(self):
        """Release network communication.
        
        Should be called after completing a communication process (e.g. after
        uploading/downloading files or completing a series of commands).
        This allows other clients to communicate with the controller.
        """
        try:
            self.send_command(CMD_RELEASE_NET_COMM, 2, 0)
        except Exception:
            # Best effort - don't fail if release command fails
            pass
    
    def _validate_driver(self, driver: str) -> int:
        """Validate driver and return driver number.
        
        Args:
            driver: Driver letter ('A', 'B', or 'C')
        
        Returns:
            Driver number (0, 1, or 2)
        
        Raises:
            SCLControllerError: If driver is invalid
        """
        if driver not in DRIVER_NAMES:
            raise SCLControllerError(f"Invalid driver: {driver} (must be A, B, or C)")
        return DRIVER_NAMES[driver]
    
    def _driver_num_to_letter(self, driver_num: int) -> str:
        """Convert driver number to letter.
        
        Args:
            driver_num: Driver number (0, 1, or 2)
        
        Returns:
            Driver letter ('A', 'B', or 'C') or 'Unknown(n)' if invalid
        """
        return DRIVER_NAMES.get(driver_num, f'Unknown({driver_num})')
    
    def _validate_remote_path(self, remote_path: str) -> None:
        """Validate remote file path length.
        
        Args:
            remote_path: Remote file path to validate
        
        Raises:
            SCLControllerError: If path is too long
        """
        if len(remote_path) > MAX_FILENAME_LENGTH:
            raise SCLControllerError(
                f"Remote path too long: {remote_path} (max {MAX_FILENAME_LENGTH} chars)"
            )
    
    def _validate_subdirectory(self, subdirectory: str) -> None:
        """Validate subdirectory name length.
        
        Args:
            subdirectory: Subdirectory name to validate
        
        Raises:
            SCLControllerError: If subdirectory name is too long
        """
        if len(subdirectory) > MAX_SUBDIRECTORY_LENGTH:
            raise SCLControllerError(
                f"Subdirectory name too long: {subdirectory} (max {MAX_SUBDIRECTORY_LENGTH} chars)"
            )
    
    def send_command(self, command: int, param1: int = 0, param2: int = 0,
                    param3: Optional[bytes] = None) -> Tuple[int, int, Optional[bytes]]:
        """
        Send a command to the controller and receive response.
        
        Args:
            command: Command code
            param1: Parameter 1
            param2: Parameter 2
            param3: Optional parameter 3 bytes
        
        Returns:
            Tuple of (response_param1, response_param2, response_param3)
        
        Raises:
            SCLControllerError: If communication fails or controller returns error
        """
        if not self.socket:
            raise SCLControllerError("Not connected. Call connect() first.")
        
        # Build basic data packet once (doesn't include packet number)
        basic_data = build_basic_data_packet(command, param1, param2, param3)
        
        max_retries = 3
        for attempt in range(max_retries):
            # Increment packet number for this attempt
            prev_packet_num = self.packet_num
            self.packet_num += 1
            logger.debug("Packet# %d -> %d (cmd=0x%08X, attempt %d/%d)", prev_packet_num, self.packet_num, command, attempt+1, max_retries)
            
            # Build packet with current packet number
            packet = build_udp_packet(self.packet_num, basic_data, self.scl2008)
            
            try:
                # Send to controller
                self.socket.sendto(packet, (self.ip_address, self.port))
                
                # Receive response - may need to handle out-of-order/stale packets
                # Try multiple times to get the correct packet
                max_recv_attempts = 5
                found_correct_packet = False
                last_resp_packet_num = None
                
                for recv_attempt in range(max_recv_attempts):
                    response_data, addr = self.socket.recvfrom(4096)
                    
                    # Parse response
                    resp_packet_num, resp_command, resp_param1, resp_param2, resp_param3 = \
                        parse_response(response_data, self.scl2008)
                    last_resp_packet_num = resp_packet_num
                    
                    # Check if this is the packet we're looking for
                    if resp_packet_num == self.packet_num:
                        found_correct_packet = True
                        break
                    else:
                        # This is a stale packet - discard and try again
                        if recv_attempt < max_recv_attempts - 1:
                            # Set a shorter timeout for subsequent receives
                            self.socket.settimeout(0.5)
                            continue
                
                # Restore original timeout
                self.socket.settimeout(self.timeout)
        
                if not found_correct_packet:
                    # Analyze the mismatch to determine appropriate action
                    if last_resp_packet_num is not None:
                        if last_resp_packet_num > self.packet_num:
                            # Controller is AHEAD - we're behind, need to catch up
                            if attempt < max_retries - 1:
                                logger.warning("Packet counter out of sync. Sent %d, controller at %d. Resyncing...", self.packet_num, last_resp_packet_num)
                                self._flush_socket_buffer()
                                # Set to controller's value - 1 so next increment matches
                                self.packet_num = last_resp_packet_num - 1
                                logger.debug("Reset packet counter to %d (next will be %d)", self.packet_num, last_resp_packet_num)
                                continue
                        elif last_resp_packet_num < self.packet_num:
                            # Received STALE response - controller hasn't responded yet
                            # This is likely a stale packet from buffer, not a real issue
                            # Just retry the same packet number without resyncing
                            if attempt < max_retries - 1:
                                logger.warning("Received stale response %d (expected %d). Retrying...", last_resp_packet_num, self.packet_num)
                                self._flush_socket_buffer()
                                # Decrement so next increment sends same number again
                                self.packet_num -= 1
                                continue
                    
                    # If we get here, we've exhausted retries
                    raise SCLControllerError(
                        f"Packet number mismatch for cmd 0x{command:08X}: sent {self.packet_num}, "
                        f"received {last_resp_packet_num} (tried {max_recv_attempts} receives, attempt {attempt+1}/{max_retries})"
                    )
                
                # Check for error response
                if resp_param2 == ERROR_CODE:
                    raise SCLControllerError(
                        f"Controller returned error for command 0x{command:08X}"
                    )
                
                return resp_param1, resp_param2, resp_param3
                
            except socket.timeout:
                if attempt == max_retries - 1:
                    raise SCLTimeoutError(
                        f"Timeout waiting for response from {self.ip_address}:{self.port}"
                    )
                # Retry on timeout
                continue
            except SCLProtocolError as e:
                raise SCLControllerError(f"Protocol error: {e}")
            except socket.error as e:
                if attempt == max_retries - 1:
                    raise SCLControllerError(f"Socket error: {e}")
                continue
        
        # Should not reach here
        raise SCLControllerError(f"Failed to get valid response after {max_retries} attempts")
    
    def _send_to_buffer(self, offset: int, data: bytes):
        """
        Send data to controller's communication buffer.
        
        Args:
            offset: Buffer offset to write at
            data: Data bytes to write
        
        Raises:
            SCLControllerError: If send fails
        """
        if len(data) > MAX_PACKET_DATA_SIZE:
            raise SCLControllerError(
                f"Data chunk too large: {len(data)} bytes (max {MAX_PACKET_DATA_SIZE})"
            )
        
        # Build param3: data payload
        param1, param2, _ = self.send_command(
            CMD_SEND_DATA_TO_BUFFER,
            offset,
            len(data),
            data
        )
        
        # Verify response
        if param1 != offset or param2 != len(data):
            raise SCLControllerError(
                f"Buffer write verification failed: expected offset={offset}, "
                f"length={len(data)}, got offset={param1}, length={param2}"
            )
    
    def _retrieve_from_buffer(self, offset: int, length: int) -> bytes:
        """
        Retrieve data from controller's communication buffer.
        
        Args:
            offset: Buffer offset to read from
            length: Number of bytes to read
        
        Returns:
            Retrieved data bytes
        
        Raises:
            SCLControllerError: If retrieval fails
        """
        param1, param2, param3 = self.send_command(
            CMD_RETRIEVE_DATA_FROM_BUFFER,
            offset,
            length
        )
        
        # Verify response parameters
        if param1 != offset:
            raise SCLControllerError(
                f"Buffer read offset mismatch: expected {offset}, got {param1}"
            )
        
        if param2 != length:
            raise SCLControllerError(
                f"Buffer read length mismatch: expected {length}, got {param2}"
            )
        
        # Check if we got data
        if param3 is None:
            raise SCLControllerError(
                f"No data received from buffer at offset {offset}"
            )
        
        # Verify data length matches requested length
        if len(param3) != length:
            raise SCLControllerError(
                f"Buffer read data mismatch: expected {length} bytes, "
                f"got {len(param3)} bytes (data: {param3[:50].hex() if len(param3) > 0 else 'empty'}...)"
            )
        
        return param3
    
    def check_status(self) -> Dict:
        """
        Read controller running status information.
        
        Returns:
            Dictionary with controller status information including:
            - total_programs: Total program count
            - current_program: Currently playing program number
            - program_driver: Driver where current program is located
            - sd_card_ready: SD card status (True if ready)
            - humidity: Humidity from sensor (%)
            - temperature: Temperature from DS18B20 (°C)
            - power_state: Power supply state (0=Off, 1=On, 2=Auto)
            - power_mode: Power mode setting
            - rtc: Real-time clock info (datetime dict)
            - brightness: LED brightness (0-30, 31=auto)
            - program_index: Which set of programs is playing
            - sw1_state: State of SW1 port
            - sw2_state: State of SW2 port
        
        Raises:
            SCLControllerError: If status read fails
        """
        param1, param2, param3 = self.send_command(CMD_READ_RUNNING_INFO, 0, 0)
        
        if param2 != 0x00000200:  # Should return 512 bytes
            raise SCLControllerError(
                f"Unexpected status response size: {param2} (expected 512)"
            )
        
        if param3 is None or len(param3) != 512:
            raise SCLControllerError(
                f"Status data size mismatch: got {len(param3) if param3 else 0} bytes"
            )
        
        # Parse runtime info structure according to RunTimeInfoStru
        # All fields are WORD (2 bytes, little-endian) unless specified otherwise
        import struct
        
        status = {}
        offset = 0
        
        try:
            # Skip reserved Start[15] = 30 bytes
            offset = 30
            
            # WORD TotalProgCount
            status['total_programs'] = struct.unpack('<H', param3[offset:offset+2])[0]
            offset += 2
            
            # WORD CurrentProg
            status['current_program'] = struct.unpack('<H', param3[offset:offset+2])[0]
            offset += 2
            
            # WORD NotUsed1 (skip)
            offset += 2
            
            # WORD ProgDrv
            prog_drv = struct.unpack('<H', param3[offset:offset+2])[0]
            status['program_driver'] = self._driver_num_to_letter(prog_drv)
            offset += 2
            
            # WORD SD_OK
            status['sd_card_ready'] = struct.unpack('<H', param3[offset:offset+2])[0] != 0
            offset += 2
            
            # WORD NotUsed2 (skip)
            offset += 2
            
            # WORD Humid
            status['humidity'] = struct.unpack('<H', param3[offset:offset+2])[0]
            offset += 2
            
            # short Temperature (signed)
            status['temperature'] = struct.unpack('<h', param3[offset:offset+2])[0]
            offset += 2
            
            # WORD PowerSwitch
            status['power_state'] = struct.unpack('<H', param3[offset:offset+2])[0]
            offset += 2
            
            # int NotUsed3 (4 bytes, skip)
            offset += 4
            
            # BYTE ProgramIndex
            status['program_index'] = param3[offset]
            offset += 1
            
            # BYTE ProgramDrv
            prog_drv_byte = param3[offset]
            status['program_driver_index'] = self._driver_num_to_letter(prog_drv_byte)
            offset += 1
            
            # WORD NotUsed4[8] (16 bytes, skip)
            offset += 16
            
            # RTC fields: 7 bytes  
            # The order in the status response is: second, minute, hour, day, month, week, year
            def from_bcd(val):
                """Convert BCD to decimal."""
                return ((val >> 4) * 10) + (val & 0x0F)
            
            # Log raw RTC bytes for debugging
            rtc_raw = param3[offset:offset+7]
            logger.debug(f"RTC raw bytes at offset {offset}: {rtc_raw.hex()} = {list(rtc_raw)}")
            
            rtc_second_raw = param3[offset]
            offset += 1
            rtc_minute_raw = param3[offset]
            offset += 1
            rtc_hour_raw = param3[offset]
            offset += 1
            rtc_day_raw = param3[offset]
            offset += 1
            rtc_month_raw = param3[offset]
            offset += 1
            rtc_week_raw = param3[offset]
            offset += 1
            rtc_year_raw = param3[offset]
            offset += 1
            
            logger.debug(f"RTC raw values: sec={rtc_second_raw}, min={rtc_minute_raw}, "
                        f"hour={rtc_hour_raw}, day={rtc_day_raw}, month={rtc_month_raw}, "
                        f"week={rtc_week_raw}, year={rtc_year_raw}")
            
            # Try BCD decode
            rtc_second = from_bcd(rtc_second_raw)
            rtc_minute = from_bcd(rtc_minute_raw)
            rtc_hour = from_bcd(rtc_hour_raw)
            rtc_day = from_bcd(rtc_day_raw)
            rtc_month = from_bcd(rtc_month_raw)
            rtc_week = from_bcd(rtc_week_raw)
            rtc_year = from_bcd(rtc_year_raw)
            
            logger.debug(f"RTC BCD decoded: sec={rtc_second}, min={rtc_minute}, "
                        f"hour={rtc_hour}, day={rtc_day}, month={rtc_month}, "
                        f"week={rtc_week}, year={rtc_year}")
            
            # Year is stored as offset from 2000 (0-99 for 2000-2099)
            rtc_year += 2000
            
            status['rtc'] = {
                'year': rtc_year,
                'month': rtc_month,
                'day': rtc_day,
                'hour': rtc_hour,
                'minute': rtc_minute,
                'second': rtc_second,
                'weekday': rtc_week  # 0=Sunday, 6=Saturday
            }
            
            # WORD Brightness
            brightness = struct.unpack('<H', param3[offset:offset+2])[0]
            status['brightness'] = brightness
            status['brightness_auto'] = (brightness == 31)
            offset += 2
            
            # WORD NotUsed5 (skip)
            offset += 2
            
            # Skip Com1Data, Com2Data, Com3Data (8*8*3 = 192 bytes)
            offset += 192
            
            # int NotUsed6[24] (96 bytes, skip)
            offset += 96
            
            # WORD NotUsed7 (skip)
            offset += 2
            
            # WORD PowerMode
            status['power_mode'] = struct.unpack('<H', param3[offset:offset+2])[0]
            offset += 2
            
            # WORD NotUsed8[7] (14 bytes, skip)
            offset += 14
            
            # WORD SW1
            status['sw1_state'] = struct.unpack('<H', param3[offset:offset+2])[0]
            offset += 2
            
            # WORD SW2
            status['sw2_state'] = struct.unpack('<H', param3[offset:offset+2])[0]
            offset += 2
            
            # Add connected flag
            status['connected'] = True
            
        except Exception as e:
            raise SCLControllerError(f"Failed to parse runtime info: {e}")
        
        return status
    
    def get_play_status(self) -> Dict:
        """
        Get current playlist playing status.
        
        Returns:
            Dictionary with play status:
            - driver: Driver where current PlayList.ly is ('A', 'B', or 'C')
            - subdirectory: Subdirectory where current PlayList.ly is
            - playlist_item: Current item in the PlayList.ly
            - area1_program: program displayed in area 1
            - area2_program: program displayed in area 2
            - area3_program: program displayed in area 3
            - area4_program: program displayed in area 4
        
        Raises:
            SCLControllerError: If status read fails
        
        Note:
            Response format per protocol spec:
            PA1: 0x00000000
            PA2: 0x00000007 (7 bytes of status data)
            PA3: 7 bytes containing:
              BYTE1: Driver where current PlayList.ly is
              BYTE2: Subdirectory where current PlayList.ly is
              BYTE3: Item in current playing PlayList.ly
              BYTE4: program displayed in area 1
              BYTE5: program displayed in area 2
              BYTE6: program displayed in area 3
              BYTE7: program displayed in area 4
        """
        from .constants import CMD_PLAY_STATUS
        
        param1, param2, param3 = self.send_command(CMD_PLAY_STATUS, 0, 0)
        
        # Verify response size
        if param2 != 7:
            raise SCLControllerError(
                f"Unexpected play status response size: {param2} (expected 7)"
            )
        
        if param3 is None or len(param3) < 7:
            raise SCLControllerError(
                f"Play status data size mismatch: got {len(param3) if param3 else 0} bytes"
            )
        
        # Parse the 7-byte status
        driver_num = param3[0]
        subdirectory = param3[1]
        playlist_item = param3[2]
        area1_program = param3[3]
        area2_program = param3[4]
        area3_program = param3[5]
        area4_program = param3[6]
        
        # Convert driver number to letter
        driver = self._driver_num_to_letter(driver_num)
        
        return {
            'driver': driver,
            'subdirectory': subdirectory,
            'playlist_item': playlist_item,
            'area1_program': area1_program,
            'area2_program': area2_program,
            'area3_program': area3_program,
            'area4_program': area4_program
        }
    
    def list_files(self, driver: str = 'A', subdirectory: str = '') -> List[Dict]:
        """
        List files on controller disk.
        
        Args:
            driver: Driver letter ('A', 'B', or 'C')
            subdirectory: Subdirectory name (max 3 chars, empty for root)
        
        Returns:
            List of dictionaries with file information
        
        Raises:
            SCLControllerError: If listing fails
        """
        # Validate and convert driver
        driver_num = self._validate_driver(driver)
        
        # Validate subdirectory length
        self._validate_subdirectory(subdirectory)
        
        # Pack subdirectory name (4 bytes with null termination)
        subdir_bytes = subdirectory.encode('ascii') + b'\x00' * (4 - len(subdirectory))
        
        # Send directory download command
        param1, param2, _ = self.send_command(
            CMD_DOWNLOAD_DIRECTORY,
            driver_num,
            0x00000004,  # Subdirectory parameter size
            subdir_bytes
        )
        
        # param1 is driver number, param2 is number of entries
        if param1 != driver_num:
            raise SCLControllerError(
                f"Driver mismatch in response: expected {driver_num}, got {param1}"
            )
        
        entry_count = param2
        if entry_count == ERROR_CODE:
            raise SCLControllerError("Failed to list directory")
        
        if entry_count == 0:
            return []
        
        # Calculate total bytes to retrieve (32 bytes per entry)
        total_bytes = entry_count * 32
        
        # Retrieve directory data from buffer
        dir_data = self._retrieve_from_buffer(0, total_bytes)
        
        # Parse directory entries
        files = []
        for i in range(entry_count):
            entry_offset = i * 32
            entry_data = dir_data[entry_offset:entry_offset + 32]
            
            try:
                entry = parse_directory_entry(entry_data)
                files.append(entry)
            except SCLProtocolError as e:
                # Skip invalid entries
                print(f"Warning: Failed to parse directory entry {i}: {e}")
                continue
        
        return files
    
    def upload_file(self, local_path: str, driver: str = 'A', 
                   remote_path: str = None, pause_controller: bool = False) -> bool:
        """
        Upload a file to the controller.
        
        Automatically converts BMP, GIF, or PNG monochrome images to XMP format
        before uploading.
        
        Args:
            local_path: Path to local file
            driver: Destination driver ('A', 'B', or 'C')
            remote_path: Remote filename (defaults to local filename)
            pause_controller: Whether to pause controller during upload
        
        Returns:
            True if upload successful
        
        Raises:
            SCLControllerError: If upload fails
        """
        # Validate driver
        driver_num = self._validate_driver(driver)
        
        # Check if file needs conversion to XMP
        converted_file = None
        is_temp = False
        actual_path = local_path
        
        try:
            if needs_conversion(local_path):
                # Convert image to XMP format
                try:
                    converted_file, is_temp = convert_to_xmp(local_path)
                    actual_path = converted_file
                    
                    # If no remote_path specified, preserve original filename with extension
                    if remote_path is None:
                        remote_path = Path(local_path).name.upper()
                except ImageConversionError as e:
                    raise SCLControllerError(f"Image conversion failed: {e}")
        
            # Read local file
            local_file = Path(actual_path)
            if not local_file.exists():
                raise SCLControllerError(f"File not found: {actual_path}")
        
            file_data = local_file.read_bytes()
            file_size = len(file_data)
        
            # Check size limit
            if file_size > COMM_BUFFER_SIZE:
                raise SCLControllerError(
                    f"File too large: {file_size} bytes (max {COMM_BUFFER_SIZE})"
                )
        
            # Determine remote filename
            if remote_path is None:
                remote_path = local_file.name
        
            # Validate filename length (max 16 chars including subdirectory)
            self._validate_remote_path(remote_path)
        
            # Pause controller if requested
            if pause_controller:
                self.send_command(CMD_PAUSE_PLAY, PAUSE_MODE, 0)
        
            try:
                # Upload file data to buffer in chunks
                offset = 0
                while offset < file_size:
                    chunk_size = min(MAX_PACKET_DATA_SIZE, file_size - offset)
                    chunk = file_data[offset:offset + chunk_size]
                    
                    self._send_to_buffer(offset, chunk)
                    offset += chunk_size
                
                # Get current date/time for file timestamp
                now = datetime.now()
                time_word, date_word = pack_dos_datetime(
                    now.year, now.month, now.day,
                    now.hour, now.minute, now.second
                )
                
                # Pack filename
                # IMPORTANT: Controller expects DOS-style backslash paths!
                # Convert forward slashes to backslashes (e.g., P00/FILE.TXT -> P00\FILE.TXT)
                remote_path_dos = remote_path.replace('/', '\\')
                filename_bytes = pack_filename(remote_path_dos, 32)
                
                # Build param3: time(2) + date(2) + filename(32)
                param3 = struct.pack('<HH', time_word, date_word) + filename_bytes
                
                # Send save command
                param1, param2, _ = self.send_command(
                    CMD_SAVE_BUFFER_TO_FILE,
                    driver_num,
                    file_size,
                    param3
                )
                
                # Verify response
                if param1 != driver_num or param2 != file_size:
                    raise SCLControllerError(
                        f"File save verification failed: expected driver={driver_num}, "
                        f"size={file_size}, got driver={param1}, size={param2}"
                    )
                
                return True
                
            finally:
                # Resume controller if we paused it
                if pause_controller:
                    try:
                        self.send_command(CMD_PAUSE_PLAY, PLAY_MODE, 0)
                    except:
                        pass  # Best effort to resume
        finally:
            # Clean up temporary converted file
            if is_temp and converted_file:
                try:
                    Path(converted_file).unlink(missing_ok=True)
                except:
                    pass  # Best effort cleanup
    
    def download_file(self, remote_path: str, local_path: str = None, 
                     driver: str = 'A', force_raw: bool = False) -> bool:
        """
        Download a file from the controller.
        
        Automatically converts XMP format files to BMP, GIF, or PNG if the local_path
        has one of those extensions, unless force_raw is True.
        
        Args:
            remote_path: Remote filename on controller (max 16 chars)
            local_path: Local destination path (defaults to current dir with remote filename)
            driver: Source driver ('A', 'B', or 'C')
            force_raw: If True, always save as raw XMP without conversion and change
                      extension to .XMP if file is detected as XMP format
        
        Returns:
            True if download successful
        
        Raises:
            SCLControllerError: If download fails
        """
        # Validate driver
        driver_num = self._validate_driver(driver)
        
        # Validate remote filename length
        self._validate_remote_path(remote_path)
        
        # Pack filename (32 bytes with null termination)
        # IMPORTANT: Controller expects DOS-style backslash paths!
        # Convert forward slashes to backslashes (e.g., P00/FILE.TXT -> P00\FILE.TXT)
        remote_path_dos = remote_path.replace('/', '\\')
        filename_bytes = pack_filename(remote_path_dos, 32)
        
        # Build PA3: Two reservation DWORDs (both 0) + 32 bytes filename
        # Protocol spec shows: Command, Driver, reservation(0), reservation(0), 32 bytes filename
        # Our structure: Command, PA1, PA2, PA3
        # So PA3 must contain: DWORD(0) + 32 bytes filename
        param3 = struct.pack('<I', 0) + filename_bytes  # reservation DWORD + filename
        
        # Send load file to buffer command
        # Protocol: PA1=Driver, PA2=0 (reservation #1), PA3=DWORD(0) + filename
        # Response: PA1=Driver, PA2=number of bytes downloaded to buffer
        param1, param2, param3_response = self.send_command(
            CMD_LOAD_FILE_TO_BUFFER,
            driver_num,
            0,  # PA2 = reservation #1 (0)
            param3  # PA3 = reservation #2 (DWORD 0) + filename (32 bytes)
        )
        
        # Verify response: param1 should be driver number
        if param1 != driver_num:
            raise SCLControllerError(
                f"Driver mismatch in response: expected {driver_num}, got {param1}"
            )
        
        # Check for error
        if param2 == ERROR_CODE:
            raise SCLControllerError(f"File not found: {remote_path}")
        
        # PA2 contains the number of bytes downloaded to buffer (i.e., file size)
        file_size = param2
        
        if file_size > COMM_BUFFER_SIZE:
            raise SCLControllerError(
                f"File too large: {file_size} bytes (max {COMM_BUFFER_SIZE})"
            )
        
        # Handle empty files
        if file_size == 0:
            # Determine local path
            if local_path is None:
                local_path = remote_path
            
            # Create empty file
            local_file = Path(local_path)
            local_file.write_bytes(b'')
            return True
        
        # Give controller a moment to ensure file is fully loaded to buffer
        # Some controllers may need time to complete the disk-to-buffer transfer
        time.sleep(0.1)
        
        # Retrieve file data from buffer
        file_data = b''
        offset = 0
        
        while offset < file_size:
            chunk_size = min(MAX_PACKET_DATA_SIZE, file_size - offset)
            chunk = self._retrieve_from_buffer(offset, chunk_size)
            
            if chunk is None:
                raise SCLControllerError(
                    f"Failed to retrieve data at offset {offset}: got None"
                )
            
            file_data += chunk
            offset += chunk_size
        
        # Verify we got all the data
        if len(file_data) != file_size:
            raise SCLControllerError(
                f"Downloaded data size mismatch: expected {file_size} bytes, "
                f"got {len(file_data)} bytes"
            )
        
        # Determine local path
        if local_path is None:
            local_path = remote_path
        
        local_file = Path(local_path)
        
        # Check if the downloaded data is XMP format
        is_xmp_format = False
        if len(file_data) >= 2:
            xmp_type = file_data[0]
            # XMP files have type byte of 1 or 2
            if xmp_type in [1, 2]:
                is_xmp_format = True
        
        # If force_raw is True and file is XMP, change extension to .XMP
        if force_raw and is_xmp_format:
            # Change extension to .XMP if not already
            if not local_file.suffix.upper() == '.XMP':
                local_file = local_file.with_suffix('.XMP')
            # Write raw XMP data
            local_file.write_bytes(file_data)
        else:
            # Check if we need to convert from XMP format to another image format
            # This happens when the local path has an image extension (.bmp, .gif, .png)
            # and the downloaded file appears to be in XMP format
            from .image_converter import is_convertible_image, convert_from_xmp, ImageConversionError
            import tempfile
            
            needs_xmp_conversion = False
            if is_xmp_format and is_convertible_image(str(local_file)):
                needs_xmp_conversion = True
            
            if needs_xmp_conversion:
                # Save XMP data to temporary file, convert, then delete temp
                temp_xmp = None
                try:
                    # Create temporary XMP file
                    fd, temp_xmp = tempfile.mkstemp(suffix='.xmp', prefix='scl_download_')
                    import os
                    os.close(fd)
                    
                    # Write XMP data to temp file
                    Path(temp_xmp).write_bytes(file_data)
                    
                    # Convert from XMP to target format
                    convert_from_xmp(temp_xmp, str(local_file))
                    
                except ImageConversionError as e:
                    # If conversion fails, just save the raw XMP data
                    local_file.write_bytes(file_data)
                finally:
                    # Clean up temporary file
                    if temp_xmp:
                        try:
                            Path(temp_xmp).unlink(missing_ok=True)
                        except:
                            pass
            else:
                # Write to local file as-is
                local_file.write_bytes(file_data)
        
        return True
    
    def download_directory(self, remote_dir: str, local_dir: str, 
                          driver: str = 'A', recursive: bool = False) -> int:
        """
        Download all files from a directory on the controller.
        
        Args:
            remote_dir: Remote directory name (max 3 chars, empty for root)
            local_dir: Local destination directory
            driver: Source driver ('A', 'B', or 'C')
            recursive: Whether to download subdirectories (not implemented yet)
        
        Returns:
            Number of files downloaded
        
        Raises:
            SCLControllerError: If download fails
        """
        if recursive:
            raise SCLControllerError("Recursive directory download not yet implemented")
        
        # Validate remote directory length
        self._validate_subdirectory(remote_dir)
        
        # Create local directory
        local_path = Path(local_dir)
        local_path.mkdir(parents=True, exist_ok=True)
        
        # List files in remote directory
        files = self.list_files(driver, remote_dir)
        
        # Filter out directories
        file_list = [f for f in files if not f['is_dir']]
        
        if not file_list:
            return 0
        
        # Download each file
        downloaded = 0
        for file_info in file_list:
            remote_filename = file_info['name']
            
            # Build remote path with subdirectory if needed
            if remote_dir:
                remote_file_path = f"{remote_dir}/{remote_filename}"
            else:
                remote_file_path = remote_filename
            
            # Local destination
            local_file_path = local_path / remote_filename
            
            try:
                self.download_file(remote_file_path, str(local_file_path), driver)
                downloaded += 1
            except SCLControllerError as e:
                # Log error but continue with other files
                print(f"Warning: Failed to download {remote_filename}: {e}")
                continue
        
        return downloaded
    
    def get_free_space(self, driver: str = 'A') -> int:
        """
        Get free space on controller disk.
        
        Args:
            driver: Driver letter ('A', 'B', or 'C')
        
        Returns:
            Free space in bytes
        
        Raises:
            SCLControllerError: If query fails
        """
        from .constants import CMD_GET_DISK_FREE_SPACE
        
        driver_num = self._validate_driver(driver)
        
        param1, param2, _ = self.send_command(
            CMD_GET_DISK_FREE_SPACE,
            driver_num,
            0
        )
        
        if param1 != driver_num:
            raise SCLControllerError(f"Driver mismatch in response")
        
        return param2
    
    # Control command methods
    
    def delete_file(self, remote_path: str, driver: str = 'A') -> bool:
        """
        Delete a file from the controller.
        
        Args:
            remote_path: Remote file path to delete (max 16 chars)
            driver: Driver letter ('A', 'B', or 'C')
        
        Returns:
            True if deletion successful
        
        Raises:
            SCLControllerError: If deletion fails
        """
        from .constants import CMD_DELETE_FILE
        
        driver_num = self._validate_driver(driver)
        self._validate_remote_path(remote_path)
        
        # Pack filename (32 bytes)
        remote_path_dos = remote_path.replace('/', '\\\\')
        filename_bytes = pack_filename(remote_path_dos, 32)
        
        # Build param3: reservation DWORD (0) + 32 bytes filename
        param3 = struct.pack('<I', 0) + filename_bytes
        
        # Send delete command
        param1, param2, _ = self.send_command(
            CMD_DELETE_FILE,
            driver_num,
            0,
            param3
        )
        
        # Check for error
        if param2 == ERROR_CODE:
            raise SCLControllerError(f"File not found or cannot be deleted: {remote_path}")
        
        # Verify response
        if param1 != driver_num:
            raise SCLControllerError(
                f"Driver mismatch in response: expected {driver_num}, got {param1}"
            )
        
        return True
    
    def pause(self) -> None:
        """Pause display playback."""
        self.send_command(CMD_PAUSE_PLAY, PAUSE_MODE, 0)
    
    def play(self) -> None:
        """Resume display playback."""
        self.send_command(CMD_PAUSE_PLAY, PLAY_MODE, 0)
    
    def set_power_mode(self, mode: int) -> None:
        """
        Set LED screen power mode.
        
        Args:
            mode: Power mode (0=Off, 1=On, 2=Auto)
        
        Raises:
            ValueError: If mode is not 0, 1, or 2
        """
        from .constants import CMD_SETUP_POWER_MODE, POWER_MODE_OFF, POWER_MODE_ON, POWER_MODE_AUTO
        
        if mode not in [POWER_MODE_OFF, POWER_MODE_ON, POWER_MODE_AUTO]:
            raise ValueError(f"Invalid power mode: {mode} (must be 0=Off, 1=On, 2=Auto)")
        
        self.send_command(CMD_SETUP_POWER_MODE, mode, 0)
    
    def set_brightness(self, brightness: int) -> None:
        """
        Set LED screen brightness.
        
        Args:
            brightness: Brightness level (0-30, where 0=darkest, 30=brightest, 31=auto)
        
        Raises:
            ValueError: If brightness is not in range 0-31
            SCLControllerError: If command fails
        """
        from .constants import CMD_SET_BRIGHTNESS, BRIGHTNESS_MIN, BRIGHTNESS_MAX, BRIGHTNESS_AUTO
        
        if not (BRIGHTNESS_MIN <= brightness <= BRIGHTNESS_AUTO):
            raise ValueError(
                f"Invalid brightness: {brightness} (must be 0-30 for manual, 31 for auto)"
            )
        
        # Pack brightness as a BYTE in param3
        param3 = struct.pack('B', brightness)
        
        param1, param2, _ = self.send_command(CMD_SET_BRIGHTNESS, 1, 5, param3)
        
        # Check response: PA2=1 for success, 0xFFFFFFFF for failure
        if param2 == ERROR_CODE:
            raise SCLControllerError(f"Failed to set brightness to {brightness}")
    
    def format_disk(self, driver: str) -> None:
        """
        Format a storage driver.
        
        Args:
            driver: Driver letter ('A', 'B', or 'C')
        
        Warning:
            This will ERASE ALL DATA on the driver!
        
        Raises:
            SCLControllerError: If format fails
        """
        from .constants import CMD_FORMAT_DISK
        
        driver_num = self._validate_driver(driver)
        self.send_command(CMD_FORMAT_DISK, driver_num, 0)
    
    def create_subdirectory(self, name: str, driver: str = 'A') -> None:
        """
        Create a subdirectory on the controller at the root level.
        
        Args:
            name: Subdirectory name (max 3 characters, e.g., 'P00', 'FON')
            driver: Driver letter ('A', 'B', or 'C')
        
        Note:
            Subdirectories can only be created at the root level of a driver.
            Nested subdirectories (subdirectories within subdirectories) are not supported.
        
        Raises:
            SCLControllerError: If creation fails
        """
        from .constants import CMD_CREATE_SUBDIRECTORY
        
        self._validate_subdirectory(name)
        driver_num = self._validate_driver(driver)
        
        # Pack subdirectory name: DWORD(0) + 32 bytes name
        name_bytes = name.encode('ascii')
        subdir_name = name_bytes + b'\x00' * (32 - len(name_bytes))
        param3 = struct.pack('<I', 0) + subdir_name
        
        param1, param2, _ = self.send_command(CMD_CREATE_SUBDIRECTORY, driver_num, 0, param3)
        
        # Check for error
        if param2 == ERROR_CODE:
            raise SCLControllerError(f"Failed to create subdirectory '{name}'")
    
    def delete_subdirectory(self, name: str, driver: str = 'A') -> None:
        """
        Delete a subdirectory from the controller at the root level.
        
        Args:
            name: Subdirectory name (max 3 characters, e.g., 'P00', 'FON')
            driver: Driver letter ('A', 'B', or 'C')
        
        Note:
            - Directory must be empty before it can be deleted.
            - Only root-level subdirectories can be deleted.
            - Nested subdirectories are not supported.
        
        Raises:
            SCLControllerError: If deletion fails
        """
        from .constants import CMD_DELETE_SUBDIRECTORY
        
        self._validate_subdirectory(name)
        driver_num = self._validate_driver(driver)
        
        # Pack subdirectory name: DWORD(0) + 32 bytes name
        name_bytes = name.encode('ascii')
        subdir_name = name_bytes + b'\x00' * (32 - len(name_bytes))
        param3 = struct.pack('<I', 0) + subdir_name
        
        param1, param2, _ = self.send_command(CMD_DELETE_SUBDIRECTORY, driver_num, 0, param3)
        
        # Check response: PA2=1 for success
        if param2 != 1:
            raise SCLControllerError(
                f"Failed to delete subdirectory '{name}'. "
                f"Ensure the directory is empty and exists on driver {driver}."
            )
    
    def set_calendar_clock(self, dt: 'datetime.datetime') -> None:
        """
        Set controller's calendar and clock.
        
        Args:
            dt: datetime object with the date and time to set
        
        Raises:
            SCLControllerError: If setting fails
            ValueError: If year is not in range 2000-2030
        
        Note:
            Due to a controller limitation, only years 2000-2030 are supported.
            Years 2031 and beyond fail to set correctly on the hardware.
        """
        from .constants import CMD_SET_CALENDAR_CLOCK
        import datetime
        
        # Extract components
        year = dt.year
        month = dt.month
        day = dt.day
        hour = dt.hour
        minute = dt.minute
        second = dt.second
        
        # Validate year range (controller limitation)
        if not (2000 <= year <= 2030):
            raise ValueError(f"Year must be between 2000 and 2030, got {year}")
        
        # Calculate weekday (0=Sunday, 6=Saturday)
        weekday = (dt.weekday() + 1) % 7  # Convert Python's Monday=0 to Sunday=0
        
        # Year offset from 2000
        year_offset = year - 2000
        
        def to_bcd(val):
            """Convert decimal to BCD."""
            return ((val // 10) << 4) | (val % 10)
        
        # Pack date/time: 7 bytes
        # Encode: year(BCD), month(BCD), day(BCD), week, hour(BCD), minute(BCD), second(BCD)
        param3 = struct.pack('BBBBBBB', 
                            to_bcd(year_offset),
                            to_bcd(month),
                            to_bcd(day),
                            to_bcd(weekday),
                            to_bcd(hour),
                            to_bcd(minute),
                            to_bcd(second))
        
        logger.info(f"Setting calendar/clock: {year}-{month:02d}-{day:02d} "
                    f"{hour:02d}:{minute:02d}:{second:02d}")
        
        self.send_command(CMD_SET_CALENDAR_CLOCK, 3, 2, param3)
    
    def set_on_off_time(self, start_hour: int, start_minute: int,
                       end_hour: int, end_minute: int, days_mask: int = 0x7F) -> None:
        """
        Set display on/off time schedule.
        
        Args:
            start_hour: Start hour (0-23)
            start_minute: Start minute (0-59)
            end_hour: End hour (0-23)
            end_minute: End minute (0-59)
            days_mask: Days bitmask (bit 0=Sunday, ..., bit 6=Saturday)
                      Default 0x7F means all days
        
        Raises:
            SCLControllerError: If setting fails
        """
        from .constants import CMD_SET_ON_OFF_TIME
        
        # Pack time schedule
        param3 = struct.pack('BBBBB', start_hour, start_minute, end_hour, end_minute, days_mask)
        
        self.send_command(CMD_SET_ON_OFF_TIME, 0, len(param3), param3)
    
    def real_time_display(self, text: str) -> None:
        """
        Send text for real-time display on LED screen.
        
        Args:
            text: Text to display (max 256 characters, ASCII only)
        
        Raises:
            SCLControllerError: If send fails
        """
        from .constants import CMD_REAL_TIME_DISPLAY
        
        # Encode text and truncate if needed
        text_bytes = text.encode('ascii', errors='replace')
        if len(text_bytes) > 256:
            text_bytes = text_bytes[:256]
        
        self.send_command(CMD_REAL_TIME_DISPLAY, 0, len(text_bytes), text_bytes)
    
    def restart_schedule(self) -> None:
        """
        Restart the schedule list playback.
        
        Raises:
            SCLControllerError: If restart fails
        """
        from .constants import CMD_RESTART_SCHEDULE
        # PA1=0 means restart schedule
        self.send_command(CMD_RESTART_SCHEDULE, 0, 0)
    
    def reset_controller(self) -> None:
        """
        Reset (reboot) the controller.
        
        Warning:
            This will reboot the controller!
        
        Raises:
            SCLControllerError: If reset fails
        """
        from .constants import CMD_RESET_CONTROLLER
        # PA1=1 means reset controller
        self.send_command(CMD_RESET_CONTROLLER, 1, 0)
