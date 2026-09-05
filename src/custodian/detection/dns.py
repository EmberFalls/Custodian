"""DNS detector family wrapper."""

from custodian.detection.base import ModelDetector


class DNSDetector(ModelDetector):
    def __init__(self, package=None) -> None:
        super().__init__("dns", package)
