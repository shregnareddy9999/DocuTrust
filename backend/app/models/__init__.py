"""SQLAlchemy ORM models matching docs/data-model.md."""

from app.models.blockchain import BlockchainErrorCode, BlockchainRecord, RecordingStatus
from app.models.document import Document, DocumentCategory, ProcessingState
from app.models.extraction import ExtractionResult, ExtractionStatus
from app.models.government_record import GovernmentRecord
from app.models.marksheet import Marksheet
from app.models.registry import RegistryRecord
from app.models.review import ReviewAction, ReviewActionType
from app.models.student import Student
from app.models.student_document import StudentDocument
from app.models.verification import VerificationResult, VerificationStatus

__all__ = [
    "BlockchainErrorCode",
    "BlockchainRecord",
    "Document",
    "DocumentCategory",
    "ExtractionResult",
    "ExtractionStatus",
    "GovernmentRecord",
    "Marksheet",
    "ProcessingState",
    "RecordingStatus",
    "RegistryRecord",
    "ReviewAction",
    "ReviewActionType",
    "Student",
    "StudentDocument",
    "VerificationResult",
    "VerificationStatus",
]
