import enum
from sqlalchemy import String, Text, Enum
from sqlalchemy.orm import Mapped, mapped_column
from app.db.base import Base

class MessageDirection(str, enum.Enum):
    INBOUND = "inbound" # From User to System
    OUTBOUND = "outbound" # From System to User

class AuditMessage(Base):
    __tablename__ = "audit_messages"

    phone_number: Mapped[str] = mapped_column(String(20), index=True)
    direction: Mapped[MessageDirection] = mapped_column(Enum(MessageDirection), index=True)
    
    # Message contents (Raw text or WhatsApp payload dump)
    content: Mapped[str] = mapped_column(Text)
    
    # WhatsApp message ID for webhook deduplication/idempotency
    wa_message_id: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=True)
    
    # Metadata for grouping conversations
    session_id: Mapped[str] = mapped_column(String(255), nullable=True, index=True)
