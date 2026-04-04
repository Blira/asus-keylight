class AsusKeylightError(Exception):
    """Base exception for asus_keylight."""


class DiscoveryError(AsusKeylightError):
    """Raised when the ASUS keyboard controller cannot be discovered."""


class ValidationError(AsusKeylightError):
    """Raised when user input is invalid."""


class TransportError(AsusKeylightError):
    """Raised when HID transport operations fail."""
