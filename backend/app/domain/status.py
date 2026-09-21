"""The fixed status enums — never redefined in domain or Task 07 callers.

Task 02 persistence models keep parallel Enum types (out of scope). Services map
by `.value`. Domain code must not import those models.
"""

from enum import Enum


class VerificationStatus(str, Enum):
    PENDING = "PENDING"
    VERIFIED_MATCH = "VERIFIED_MATCH"
    REVIEW_REQUIRED = "REVIEW_REQUIRED"
    NO_TRUSTED_RECORD = "NO_TRUSTED_RECORD"
    INTEGRITY_MISMATCH = "INTEGRITY_MISMATCH"
    PROCESSING_FAILED = "PROCESSING_FAILED"


class RecordingStatus(str, Enum):
    NOT_REQUESTED = "NOT_REQUESTED"
    PENDING = "PENDING"
    CONFIRMED = "CONFIRMED"
    FAILED = "FAILED"
