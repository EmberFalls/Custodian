"""Optional passive interface capture using a platform-neutral pcap backend."""

from __future__ import annotations

import sys
from dataclasses import dataclass
from typing import Protocol

from custodian.core.schemas import PacketObservation
from custodian.ingest.pcap import SUPPORTED_DATALINKS
from custodian.parsing.packet import PacketParser

LIVE_CAPTURE_SNAPLEN = 65_535
LIVE_CAPTURE_TIMEOUT_MS = 100
MAX_CAPTURE_FILTER_CHARS = 512


class CaptureBackendError(RuntimeError):
    """Base error for optional live capture failures."""


class CaptureBackendUnavailable(CaptureBackendError):
    """Raised when the optional pcap library is not installed."""


class InterfaceUnavailable(CaptureBackendError):
    """Raised when an explicitly requested interface is no longer available."""


class CapturePermissionError(CaptureBackendError):
    """Raised when the selected interface cannot be opened for passive capture."""


class UnsupportedLinkType(CaptureBackendError):
    """Raised for capture link types the packet observation parser cannot handle."""


@dataclass(frozen=True, slots=True)
class CaptureInterface:
    interface_id: str
    name: str
    description: str
    available: bool = True
    link_type: int | None = None


class PcapHandle(Protocol):
    def datalink(self) -> int: ...

    def setfilter(self, expression: str) -> None: ...

    def next(self): ...

    def close(self) -> None: ...


class CaptureBackend(Protocol):
    def list_interfaces(self) -> list[CaptureInterface]: ...

    def open_interface(self, interface_id: str, *, snaplen: int, timeout_ms: int) -> PcapHandle:
        ...


class PcapyBackend:
    """Adapter around pcapy-ng, which delegates to Npcap/libpcap."""

    @staticmethod
    def _module():
        try:
            import pcapy
        except ImportError as exc:
            raise CaptureBackendUnavailable(
                "live capture backend is missing; install the optional 'capture' extra "
                "and the platform's Npcap/libpcap backend"
            ) from exc
        return pcapy

    def list_interfaces(self) -> list[CaptureInterface]:
        pcapy = self._module()
        try:
            names = pcapy.findalldevs()
        except Exception as exc:
            raise CaptureBackendError(f"could not enumerate capture interfaces: {exc}") from exc
        return [CaptureInterface(str(name), str(name), str(name)) for name in names if str(name)]

    def open_interface(self, interface_id: str, *, snaplen: int, timeout_ms: int) -> PcapHandle:
        pcapy = self._module()
        try:
            return pcapy.open_live(interface_id, snaplen, 0, timeout_ms)
        except Exception as exc:
            message = str(exc)
            lowered = message.lower()
            if any(term in lowered for term in ("permission", "access denied", "not permitted")):
                raise CapturePermissionError(
                    "capture permission denied for the selected interface; check Npcap/libpcap permissions"
                ) from exc
            if any(term in lowered for term in ("no such device", "device not found", "not found")):
                raise InterfaceUnavailable(
                    f"selected interface {interface_id!r} is unavailable"
                ) from exc
            raise CaptureBackendError(f"could not open selected interface: {message}") from exc


class LiveCaptureSource:
    """Read bounded packet records and return header-derived observations only."""

    def __init__(
        self,
        interface: CaptureInterface,
        handle: PcapHandle,
        datalink: int,
        capture_filter: str | None,
    ) -> None:
        self.interface = interface
        self.handle = handle
        self.datalink = datalink
        self.capture_filter = capture_filter
        self.parser = PacketParser()
        self.closed = False

    @classmethod
    def open(
        cls,
        backend: CaptureBackend,
        interface_id: str,
        capture_filter: str | None = None,
    ) -> LiveCaptureSource:
        interfaces = backend.list_interfaces()
        selected = next((item for item in interfaces if item.interface_id == interface_id), None)
        if selected is None:
            raise InterfaceUnavailable(
                "selected interface is unavailable; refresh the interface list and select one explicitly"
            )
        expression = capture_filter.strip() if capture_filter and capture_filter.strip() else None
        if expression and len(expression) > MAX_CAPTURE_FILTER_CHARS:
            raise ValueError(f"capture filter cannot exceed {MAX_CAPTURE_FILTER_CHARS} characters")
        handle = backend.open_interface(
            selected.interface_id,
            snaplen=LIVE_CAPTURE_SNAPLEN,
            timeout_ms=LIVE_CAPTURE_TIMEOUT_MS,
        )
        try:
            try:
                datalink = int(handle.datalink())
            except Exception as exc:
                raise CaptureBackendError(f"could not read selected interface link type: {exc}") from exc
            if datalink not in SUPPORTED_DATALINKS:
                raise UnsupportedLinkType(
                    f"unsupported interface link type {datalink}; Ethernet, Linux cooked, "
                    "or raw IP is required"
                )
            if expression is not None:
                try:
                    handle.setfilter(expression)
                except ValueError:
                    raise
                except Exception as exc:
                    raise CaptureBackendError(f"could not apply capture filter: {exc}") from exc
        except Exception:
            handle.close()
            raise
        selected = CaptureInterface(
            selected.interface_id,
            selected.name,
            selected.description,
            selected.available,
            datalink,
        )
        return cls(selected, handle, datalink, expression)

    def next_observation(self) -> PacketObservation | None:
        if self.closed:
            return None
        try:
            header, data = self.handle.next()
        except Exception as exc:
            if self.closed:
                return None
            raise CaptureBackendError(f"capture stopped unexpectedly: {exc}") from exc
        if header is None:
            return None
        seconds, microseconds = header.getts()
        timestamp = float(seconds) + float(microseconds) / 1_000_000
        return self.parser.parse(
            timestamp,
            data,
            self.datalink,
            wire_length=int(header.getlen()),
        )

    def close(self) -> None:
        if self.closed:
            return
        self.closed = True
        self.handle.close()


def capture_backend_status(backend: CaptureBackend) -> dict[str, object]:
    try:
        interfaces = backend.list_interfaces()
    except CaptureBackendUnavailable as exc:
        return {
            "status": "unavailable",
            "platform": sys.platform,
            "backend": "Npcap/libpcap via pcapy-ng",
            "reason": str(exc),
            "interfaces": [],
        }
    except CaptureBackendError as exc:
        return {
            "status": "degraded",
            "platform": sys.platform,
            "backend": "Npcap/libpcap via pcapy-ng",
            "reason": str(exc),
            "interfaces": [],
        }
    return {
        "status": "ready" if interfaces else "unavailable",
        "platform": sys.platform,
        "backend": "Npcap/libpcap via pcapy-ng",
        "reason": None if interfaces else "no capture interfaces are available",
        "interfaces": [
            {
                "interface_id": item.interface_id,
                "name": item.name,
                "description": item.description,
                "available": item.available,
                "link_type": item.link_type,
            }
            for item in interfaces
        ],
    }
