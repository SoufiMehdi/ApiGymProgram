from sqlalchemy import Column, Integer, String, Date
from sqlalchemy.orm import declarative_base

Base = declarative_base()

class TrainingCycle(Base):
    __tablename__ = "training_cycles"

    id = Column(Integer, primary_key=True, index=True)
    date = Column(Date, unique=True, nullable=False, index=True)  # Date du jour
    cycle_day = Column(String, nullable=False)  # "dos_biceps", "pecs_triceps", "jambes_abdos"
    muscles = Column(String, nullable=False)  # "back,biceps" ou "chest,triceps" ou "legs,abs"
    is_completed = Column(Integer, default=0)  # 0 = non fait, 1 = fait