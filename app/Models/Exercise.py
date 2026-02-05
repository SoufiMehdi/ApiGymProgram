from sqlalchemy import Column, Integer, String, Text, DateTime
from sqlalchemy.orm import declarative_base

Base = declarative_base()

class Exercise(Base):
    __tablename__ = "exercises"

    id = Column(Integer, primary_key=True, index=True)
    exercise_id = Column(String, unique=True, nullable=False, index=True)  # ID de ExerciseDB
    name_en = Column(String, nullable=False)  # Nom anglais original
    name_fr = Column(String, nullable=False)  # Nom traduit en français
    body_part = Column(String, nullable=False, index=True)  # Partie du corps (chest, back, etc.)
    target_muscle = Column(String, nullable=False)  # Muscle ciblé
    equipment = Column(String)  # Équipement nécessaire
    instructions_en = Column(Text)  # Instructions en anglais
    instructions_fr = Column(Text)  # Instructions en français
    gif_url = Column(String)  # URL du GIF original
    gif_local_path = Column(String)  # Chemin local du GIF téléchargé
    video_url = Column(String)  # URL de la vidéo originale
    video_local_path = Column(String)  # Chemin local de la vidéo
    created_at = Column(DateTime, nullable=False)
    updated_at = Column(DateTime, nullable=False)