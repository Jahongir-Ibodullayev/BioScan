"""Domain exception hierarchy.

Layers:
  TogaiError                    — root
    ExternalServiceError        — 3rd-party API failures (iNat, GBIF, Wiki, Vision)
      UpstreamTimeoutError      — request took too long
      UpstreamUnavailableError  — 5xx or network error
      UpstreamBadResponseError  — 4xx or malformed payload
    IdentificationError         — AI scan domain
      ImageProcessingError      — compress/decode failed
      VisionModelError          — all vision models failed
      LowConfidenceError        — AI confidence below threshold
    DomainError                 — business-rule violations
      SpeciesNotFoundError
      InvalidScanInputError

Every view should catch TogaiError and render a consistent JSON envelope.
"""
from __future__ import annotations


class TogaiError(Exception):
    """Base — all domain errors inherit from this."""
    status_code: int = 500
    code: str = "togai_error"

    def __init__(self, message: str = "", *, detail: dict | None = None):
        super().__init__(message)
        self.message = message or self.__class__.__name__
        self.detail = detail or {}


# ---------------- External ----------------
class ExternalServiceError(TogaiError):
    status_code = 502
    code = "upstream_error"


class UpstreamTimeoutError(ExternalServiceError):
    code = "upstream_timeout"
    status_code = 504


class UpstreamUnavailableError(ExternalServiceError):
    code = "upstream_unavailable"
    status_code = 502


class UpstreamBadResponseError(ExternalServiceError):
    code = "upstream_bad_response"
    status_code = 502


# ---------------- Identification ----------------
class IdentificationError(TogaiError):
    code = "identification_error"
    status_code = 500


class ImageProcessingError(IdentificationError):
    code = "image_processing_failed"
    status_code = 400


class VisionModelError(IdentificationError):
    code = "vision_failed"
    status_code = 502


class LowConfidenceError(IdentificationError):
    code = "low_confidence"
    status_code = 200  # not really an error — just soft signal


# ---------------- Domain ----------------
class DomainError(TogaiError):
    code = "domain_error"
    status_code = 400


class SpeciesNotFoundError(DomainError):
    code = "species_not_found"
    status_code = 404


class InvalidScanInputError(DomainError):
    code = "invalid_scan_input"
    status_code = 400
