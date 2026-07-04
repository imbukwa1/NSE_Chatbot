from datetime import datetime, timezone

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text

from database import Base


class KnowledgeBaseEntry(Base):
    __tablename__ = "knowledge_base_entries"

    id = Column(Integer, primary_key=True, index=True)
    source_id = Column(String(50), nullable=True, index=True)
    slug = Column(String(255), nullable=True, index=True)
    category = Column(String(80), nullable=False, index=True)
    subcategory = Column(String(120), nullable=True, index=True)
    question = Column(String(255), nullable=False, index=True)
    aliases = Column(Text, nullable=True)
    answer = Column(Text, nullable=False)
    answer_markdown = Column(Text, nullable=True)
    keywords = Column(Text, nullable=True)
    difficulty = Column(String(40), nullable=True, index=True)
    related_questions = Column(Text, nullable=True)
    source = Column(String(255), nullable=True)
    embedding_model = Column(String(120), nullable=True)
    embedding_content_hash = Column(String(64), nullable=True, index=True)
    pinecone_vector_id = Column(String(120), nullable=True, index=True)
    pinecone_synced_at = Column(DateTime, nullable=True)
    created_by = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)
    created_at = Column(DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(
        DateTime,
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )
