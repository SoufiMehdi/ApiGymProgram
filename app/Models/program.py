from sqlalchemy import Column, Integer, String, JSON, DateTime
from sqlalchemy.orm import declarative_base

Base = declarative_base()

class Programme(Base):
    __tablename__ = "programmes"

    id = Column(Integer, primary_key=True, index=True)
    groupes = Column(String, nullable=False)  # "dos biceps"
    contenu = Column(JSON, nullable=False)
    ia = Column(String, nullable=False)  # "gemini" ou "claude"
    created_at = Column(DateTime, nullable=False)