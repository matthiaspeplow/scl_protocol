"""
Constants for SCL Protocol communication with LyTech LED controllers.
"""

# Protocol leading codes (magic strings)
LEADING_CODE_PC_SCL2008 = b'TCLY'  # PC to Controller (SCL2008)
LEADING_CODE_CONTROLLER_SCL2008 = b'tClY'  # Controller to PC (SCL2008)
LEADING_CODE_PC_SUPERCOMM = b'LYTC'  # PC to Controller (SuperComm)
LEADING_CODE_CONTROLLER_SUPERCOMM = b'Lytc'  # Controller to PC (SuperComm)

# Command codes
CMD_SEND_DATA_TO_BUFFER = 0x00000000  # Send data to controller's communication buffer
CMD_RETRIEVE_DATA_FROM_BUFFER = 0x00000001  # Retrieve data from communication buffer
CMD_SAVE_BUFFER_TO_FILE = 0x00000002  # Save communication buffer to disk file
CMD_LOAD_FILE_TO_BUFFER = 0x00000003  # Download file from disc to buffer
CMD_DELETE_FILE = 0x00000004  # Delete file from disk
CMD_GET_DISK_FREE_SPACE = 0x00000005  # Fetch disc free space
CMD_DOWNLOAD_DIRECTORY = 0x00000006  # Download directory listing to buffer
CMD_FORMAT_DISK = 0x00000007  # Format disk
CMD_SET_CALENDAR_CLOCK = 0x00000009  # Check/set controller's calendar and clock
CMD_PAUSE_PLAY = 0x0000000A  # Pause or continue play
CMD_SET_ON_OFF_TIME = 0x0000000B  # Setup LED screen switching on/off time
CMD_SETUP_POWER_MODE = 0x0000000C  # Setup LED screen's power mode
CMD_CREATE_SUBDIRECTORY = 0x0000000D  # Create subdirectory
CMD_DELETE_SUBDIRECTORY = 0x0000000E  # Delete subdirectory
CMD_REAL_TIME_DISPLAY = 0x0000000F  # Real time display words
CMD_PLAY_STATUS = 0x00000012  # Playing status (returns 1=playing, 0=paused)
CMD_READ_RUNNING_INFO = 0x00000084  # Read running info (512 bytes)
CMD_RESTART_SCHEDULE = 0x000055AA  # Restart schedule list (with PA1=0)
CMD_RESET_CONTROLLER = 0x000055AA  # Reset controller (with PA1=1)
CMD_RELEASE_NET_COMM = 0x000055AA  # Release net communication (with PA1=2)

# Driver numbers (disk drives on controller)
DRIVER_FLASH = 0  # Disc A - FLASH memory
DRIVER_SD_CARD = 1  # Disc B - SD card
DRIVER_RAM = 2  # Disc C - RAM

# Driver name mapping
DRIVER_NAMES = {
    'A': DRIVER_FLASH,
    'B': DRIVER_SD_CARD,
    'C': DRIVER_RAM,
    DRIVER_FLASH: 'A',
    DRIVER_SD_CARD: 'B',
    DRIVER_RAM: 'C'
}

# Error codes
ERROR_CODE = 0xFFFFFFFF  # Standard error response in PA2
SUCCESS_CODE = 1  # Standard success response

# Communication buffer limits
COMM_BUFFER_SIZE = 2 * 1024 * 1024  # 2MB communication buffer
MAX_PACKET_DATA_SIZE = 1024  # Maximum data bytes per packet
MAX_BASIC_PACKET_SIZE = 1036  # Maximum basic data packet size

# UDP packet structure constants
UDP_HEADER_SIZE = 12  # 4 (leading) + 4 (packet#) + 2 (length) + 2 (reserved)
BASIC_DATA_HEADER_SIZE = 12  # 4 (command) + 4 (PA1) + 4 (PA2)

# File path constants
MAX_FILENAME_LENGTH = 16  # Maximum filename length (including subdirectory)
MAX_SUBDIRECTORY_LENGTH = 3  # Maximum subdirectory name length
FILENAME_BUFFER_SIZE = 32  # Size of filename field in packets

# Directory entry structure (32 bytes total)
DIR_ENTRY_SIZE = 32
DIR_ENTRY_FILENAME_OFFSET = 0  # Bytes 1-8
DIR_ENTRY_FILENAME_SIZE = 8
DIR_ENTRY_EXTENSION_OFFSET = 8  # Bytes 9-11
DIR_ENTRY_EXTENSION_SIZE = 3
DIR_ENTRY_ATTR_OFFSET = 11  # Byte 12
DIR_ENTRY_TIME_OFFSET = 22  # Bytes 23-24
DIR_ENTRY_DATE_OFFSET = 24  # Bytes 25-26
DIR_ENTRY_SIZE_OFFSET = 28  # Bytes 29-32

# File attributes
ATTR_FILE = 0x00
ATTR_SUBDIRECTORY = 0x10

# Power modes
POWER_MODE_OFF = 0
POWER_MODE_ON = 1
POWER_MODE_AUTO = 2

# Pause/Play modes
PAUSE_MODE = 0
PLAY_MODE = 1

# Brightness values
BRIGHTNESS_MIN = 0
BRIGHTNESS_MAX = 30
BRIGHTNESS_AUTO = 31

# Timeout settings
DEFAULT_TIMEOUT = 5  # seconds
DEFAULT_RETRY_COUNT = 3

# Default ports
DEFAULT_UDP_PORT = 1024  # LyTech controller default port
