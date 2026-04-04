class VivorgbError(Exception):
    """Base exception for vivorgb."""


class DiscoveryError(VivorgbError):
    """Raised when the ASUS keyboard controller cannot be discovered."""


class ValidationError(VivorgbError):
    """Raised when user input is invalid."""


class TransportError(VivorgbError):
    """Raised when HID transport operations fail."""
