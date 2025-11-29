"""
Exception classes for SCL Protocol module.
"""


class SCLProtocolError(Exception):
    """
    Base exception for all SCL protocol errors.
    
    This is the root exception for all protocol-related errors.
    All other SCL exceptions inherit from this class.
    """
    pass


class SCLControllerError(SCLProtocolError):
    """
    Exception raised for controller communication errors.
    
    This includes errors during UDP communication, command failures,
    and controller-reported errors.
    """
    pass


class SCLConnectionError(SCLControllerError):
    """
    Exception raised for connection-specific errors.
    
    This includes socket creation failures, connection setup issues,
    and network connectivity problems.
    """
    pass


class SCLTimeoutError(SCLControllerError):
    """
    Exception raised for timeout errors.
    
    This is raised when the controller does not respond within
    the configured timeout period.
    """
    pass


class ImageConversionError(SCLProtocolError):
    """
    Exception raised for image conversion errors.
    
    This includes errors during image loading, format validation,
    and XMP format generation.
    """
    pass
