from sqlalchemy import Column, Integer, String, Text, DateTime
from sqlalchemy.orm import declarative_base

Base = declarative_base()

class Exercise(Base):
    __tablename__ = "stat"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String)