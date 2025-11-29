"""
SCL Protocol - Python library for LyTech LED controller communication.

This module provides a complete implementation of the SCL/SuperComm protocol
for communicating with LyTech LED controllers via UDP, including support for
file operations and automatic image conversion to XMP format.

Main classes:
    SCLController: Main interface for controller communication

Exceptions:
    SCLProtocolError: Base exception for protocol errors
    SCLControllerError: Controller communication errors
    SCLConnectionError: Connection-specific errors
    SCLTimeoutError: Timeout errors
    ImageConversionError: Image conversion errors

Functions:
    convert_to_xmp: Convert BMP/GIF/PNG to XMP format
    convert_from_xmp: Convert XMP format to BMP/GIF/PNG
    needs_conversion: Check if file needs conversion

Example usage:
    >>> from scl_protocol import SCLController
    >>> with SCLController('192.168.1.100') as controller:
    ...     status = controller.check_status()
    ...     files = controller.list_files(driver='A')
    ...     controller.upload_file('test.txt', driver='A')
"""

__version__ = '0.9.0'
__author__ = 'Matthias Peplow'

from .controller import SCLController
from .exceptions import (
    SCLProtocolError,
    SCLControllerError,
    SCLConnectionError,
    SCLTimeoutError,
    ImageConversionError,
)
from .image_converter import convert_to_xmp, convert_from_xmp, needs_conversion
from .constants import (
    DRIVER_FLASH,
    DRIVER_SD_CARD,
    DRIVER_RAM,
    DRIVER_NAMES,
    DEFAULT_UDP_PORT,
)

__all__ = [
    # Main class
    'SCLController',
    # Exceptions
    'SCLProtocolError',
    'SCLControllerError',
    'SCLConnectionError',
    'SCLTimeoutError',
    'ImageConversionError',
    # Image conversion
    'convert_to_xmp',
    'convert_from_xmp',
    'needs_conversion',
    # Constants
    'DRIVER_FLASH',
    'DRIVER_SD_CARD',
    'DRIVER_RAM',
    'DRIVER_NAMES',
    'DEFAULT_UDP_PORT',
]
