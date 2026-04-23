from sqlalchemy import create_engine, Column, Integer, String, Text, DateTime, ForeignKey, event
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship, Session
from sqlalchemy.pool import StaticPool
from datetime import datetime
from app.core.config import settings
import logging

logger = logging.getLogger(__name__)


# Use default engine for PostgreSQL
engine = create_engine(
    settings.database_url,
    echo=False
)

SessionLocal = sessionmaker(autocommit=False, autoflush=True, bind=engine, expire_on_commit=False)
Base = declarative_base()

class Tenant(Base):
    __tablename__ = "tenants"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, index=True)

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True)
    hashed_password = Column(String)
    tenant_id = Column(Integer, ForeignKey("tenants.id"))
    tenant = relationship("Tenant")

class Document(Base):
    __tablename__ = "documents"
    id = Column(Integer, primary_key=True, index=True)
    filename = Column(String)
    content = Column(Text)
    tenant_id = Column(Integer, ForeignKey("tenants.id"))
    tenant = relationship("Tenant")
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

class DocumentChunk(Base):
    __tablename__ = "document_chunks"
    id = Column(Integer, primary_key=True, index=True)
    document_id = Column(Integer, ForeignKey("documents.id"))
    chunk_text = Column(Text)
    embedding = Column(Text)  # JSON string
    document = relationship("Document")

class ChatSession(Base):
    __tablename__ = "chat_sessions"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    title = Column(String)
    created_at = Column(DateTime, default=datetime.utcnow)
    user = relationship("User")

class ChatMessage(Base):
    __tablename__ = "chat_messages"
    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(Integer, ForeignKey("chat_sessions.id"))
    role = Column(String)  # user or assistant
    content = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)
    session = relationship("ChatSession")

class SavedItem(Base):
    __tablename__ = "saved_items"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    item_type = Column(String)  # 'document' or 'response'
    title = Column(String)
    content = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)
    user = relationship("User")

def create_tables():
    """Create all database tables. Safe to call multiple times."""
    try:
        Base.metadata.create_all(bind=engine)
        logger.info("✓ Database tables created/verified successfully")
        return True
    except Exception as e:
        logger.error(f"✗ Failed to create tables: {str(e)}")
        raise

def get_db():
    """Get database session with proper error handling."""
    db = SessionLocal()
    try:
        # Test the connection (fixed SQL syntax)
        from sqlalchemy import text
        db.execute(text("SELECT 1"))
        logger.debug("✓ Database connection verified")
        yield db
    except Exception as e:
        logger.error(f"✗ Database session error: {str(e)}")
        db.close()
        raise
    finally:
        db.close()

def init_default_tenant(db: Session):
    """Initialize default tenant if it doesn't exist."""
    try:
        default_tenant = db.query(Tenant).filter(Tenant.name == "default").first()
        if not default_tenant:
            default_tenant = Tenant(name="default")
            db.add(default_tenant)
            db.commit()
            logger.info("✓ Default tenant created")
        return default_tenant
    except Exception as e:
        logger.error(f"✗ Failed to initialize default tenant: {str(e)}")
        db.rollback()
        raise