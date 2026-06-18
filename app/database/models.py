from sqlalchemy import Column, Integer, String, Text, Float, Enum, Index, DateTime
from sqlalchemy.dialects.postgresql import TSVECTOR
from pgvector.sqlalchemy import Vector
from .connection import Base
import enum

class ChunkType(str, enum.Enum):
    CODE = "CODE"
    DOC = "DOC"
    ISSUE = "ISSUE"

class Chunk(Base):
    __tablename__ = "chunks"

    id = Column(Integer, primary_key=True, index=True)
    content = Column(Text, nullable=False)
    type = Column(Enum(ChunkType), nullable=False)
    source_file = Column(String, index=True)
    repository = Column(String, index=True, default="httpx")
    start_line = Column(Integer, nullable=True)
    
    # Semantic Metadata
    heading = Column(String, nullable=True)
    parent_heading = Column(String, nullable=True)
    doc_type = Column(String, nullable=True)
    
    # BAAI/bge-small-en-v1.5 has an embedding dimension of 384
    embedding = Column(Vector(384))
    
    # PostgreSQL Full Text Search vector
    fts_vector = Column(TSVECTOR)
    
    __table_args__ = (
        Index('ix_chunks_fts_vector', 'fts_vector', postgresql_using='gin'),
        Index('ix_chunks_embedding', 'embedding', postgresql_using='hnsw', postgresql_with={'m': 16, 'ef_construction': 64}, postgresql_ops={'embedding': 'vector_cosine_ops'})
    )

class Incident(Base):
    __tablename__ = "incidents"

    id = Column(Integer, primary_key=True, index=True)
    symptom = Column(Text, nullable=False)
    cause = Column(Text, nullable=False)
    fix = Column(Text, nullable=False)
    issue_url = Column(String, nullable=False)
    commit_sha = Column(String, nullable=False)

class IngestionJob(Base):
    __tablename__ = "ingestion_jobs"

    id = Column(Integer, primary_key=True, index=True)
    repo_url = Column(String, nullable=False)
    status = Column(String, nullable=False) # queued, cloning, parsing, embedding, ready, failed
    error_message = Column(String, nullable=True)
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)

class EvalResult(Base):
    __tablename__ = "eval_results"

    id = Column(Integer, primary_key=True, index=True)
    question = Column(Text, nullable=False)
    category = Column(String, nullable=False)
    hit = Column(Integer)  # rank of the hit
    latency = Column(Float)
    citation_correct = Column(Integer)  # 1 for correct, 0 for incorrect
    answer_correct = Column(Integer) # 1 for correct, 0 for incorrect
