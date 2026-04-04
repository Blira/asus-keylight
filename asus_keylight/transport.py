from __future__ import annotations

import array
import ctypes
import ctypes.util
import fcntl
import os
from pathlib import Path

from asus_keylight.errors import TransportError

_IOC_NRBITS = 8
_IOC_TYPEBITS = 8
_IOC_SIZEBITS = 14
_IOC_DIRBITS = 2

_IOC_NRSHIFT = 0
_IOC_TYPESHIFT = _IOC_NRSHIFT + _IOC_NRBITS
_IOC_SIZESHIFT = _IOC_TYPESHIFT + _IOC_TYPEBITS
_IOC_DIRSHIFT = _IOC_SIZESHIFT + _IOC_SIZEBITS

_IOC_WRITE = 1
_IOC_READ = 2


def _ioc(direction: int, ioc_type: int, nr: int, size: int) -> int:
    return (
        (direction << _IOC_DIRSHIFT)
        | (ioc_type << _IOC_TYPESHIFT)
        | (nr << _IOC_NRSHIFT)
        | (size << _IOC_SIZESHIFT)
    )


def _hid_iocsfeature(length: int) -> int:
    return _ioc(_IOC_WRITE | _IOC_READ, ord("H"), 0x06, length)


def _hid_iocgfeature(length: int) -> int:
    return _ioc(_IOC_WRITE | _IOC_READ, ord("H"), 0x07, length)


class HidApiTransport:
    def __init__(self, device_path: Path):
        self.device_path = device_path
        self._device = None

    def __enter__(self) -> "HidApiTransport":
        try:
            import hid  # type: ignore
        except ImportError as exc:
            raise TransportError("hidapi backend unavailable") from exc

        self._device = hid.Device(path=str(self.device_path).encode("utf-8"))
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        if self._device is not None:
            self._device.close()
            self._device = None

    def send_feature_report(self, packet: bytes) -> None:
        if self._device is None:
            raise TransportError("hidapi device not open")
        try:
            self._device.send_feature_report(packet)
        except OSError as exc:
            raise TransportError(f"hidapi feature report failed: {exc}") from exc

    def get_feature_report(self, report_id: int, length: int) -> bytes:
        if self._device is None:
            raise TransportError("hidapi device not open")
        try:
            return bytes(self._device.get_feature_report(report_id, length))
        except OSError as exc:
            raise TransportError(f"hidapi get feature report failed: {exc}") from exc


class HidrawIoctlTransport:
    def __init__(self, device_path: Path):
        self.device_path = device_path
        self._fd: int | None = None

    def __enter__(self) -> "HidrawIoctlTransport":
        try:
            self._fd = os.open(self.device_path, os.O_RDWR | os.O_CLOEXEC)
        except OSError as exc:
            raise TransportError(f"cannot open hidraw device {self.device_path}: {exc}") from exc
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        if self._fd is not None:
            os.close(self._fd)
            self._fd = None

    def send_feature_report(self, packet: bytes) -> None:
        if self._fd is None:
            raise TransportError("hidraw device not open")
        buffer = array.array("B", packet)
        try:
            fcntl.ioctl(self._fd, _hid_iocsfeature(len(packet)), buffer, True)
        except OSError as exc:
            raise TransportError(f"hidraw ioctl feature report failed: {exc}") from exc

    def get_feature_report(self, report_id: int, length: int) -> bytes:
        if self._fd is None:
            raise TransportError("hidraw device not open")
        buffer = array.array("B", [0] * length)
        buffer[0] = report_id
        try:
            fcntl.ioctl(self._fd, _hid_iocgfeature(length), buffer, True)
        except OSError as exc:
            raise TransportError(f"hidraw ioctl get feature report failed: {exc}") from exc
        return bytes(buffer)


class HidTransport:
    def __init__(self, device_path: Path, preferred_backend: str = "auto"):
        self.device_path = device_path
        self.preferred_backend = preferred_backend
        self.backend_name = ""
        self._backend = None

    @staticmethod
    def hidapi_available() -> bool:
        try:
            import hid  # type: ignore  # noqa: F401
        except ImportError:
            return False
        return True

    @staticmethod
    def hidapi_library_present() -> bool:
        return ctypes.util.find_library("hidapi-hidraw") is not None or ctypes.util.find_library("hidapi-libusb") is not None

    def __enter__(self) -> "HidTransport":
        backend_order = []
        if self.preferred_backend == "hidapi":
            backend_order = [("hidapi", HidApiTransport), ("hidraw", HidrawIoctlTransport)]
        elif self.preferred_backend == "hidraw":
            backend_order = [("hidraw", HidrawIoctlTransport)]
        else:
            backend_order = [("hidapi", HidApiTransport), ("hidraw", HidrawIoctlTransport)]

        errors: list[str] = []
        for backend_name, backend_cls in backend_order:
            try:
                backend = backend_cls(self.device_path)
                backend.__enter__()
                self.backend_name = backend_name
                self._backend = backend
                return self
            except TransportError as exc:
                errors.append(str(exc))
        raise TransportError("; ".join(errors))

    def __exit__(self, exc_type, exc, tb) -> None:
        if self._backend is not None:
            self._backend.__exit__(exc_type, exc, tb)
            self._backend = None

    def send_feature_report(self, packet: bytes) -> None:
        if self._backend is None:
            raise TransportError("transport backend not open")
        self._backend.send_feature_report(packet)

    def get_feature_report(self, report_id: int, length: int) -> bytes:
        if self._backend is None:
            raise TransportError("transport backend not open")
        return self._backend.get_feature_report(report_id, length)
