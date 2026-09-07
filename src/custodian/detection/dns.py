"""DNS detector family wrapper."""

from custodian.detection.base import ModelDetector


class DNSDetector(ModelDetector):
    def __init__(self, package=None, *, detector_id: str = "dns") -> None:
        super().__init__(detector_id, package)
