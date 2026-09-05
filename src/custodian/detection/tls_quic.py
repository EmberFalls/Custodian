"""TLS/QUIC metadata detector family wrapper."""

from custodian.detection.base import ModelDetector


class TLSQUICDetector(ModelDetector):
    def __init__(self, package=None) -> None:
        super().__init__("tls_quic", package)
