import datetime
from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional, List

from app.database import engine, get_db
from app.Models.Exercise import Base, Exercise
from app.Models.program import  Programme
from app.Models.TrainingCycle  import TrainingCycle
from app.ia import generer_programme
from app.Service.ExercisedbService import (
    get_exercises_by_muscle,
)

# Créer les tables
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="Iron Pulse API",
    description="API de génération de programmes d'entraînement avec IA Et ExerciceDB",
    version="3.0.0"
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Servir les médias statiques
import os
os.makedirs("media/gifs", exist_ok=True)
os.makedirs("media/videos", exist_ok=True)
app.mount("/media", StaticFiles(directory="media"), name="media")

# Schémas Pydantic
class ProgrammeRequest(BaseModel):
    groupes: str
    objectif: str = "prise de masse"
    niveau: str = "intermédiaire"
    duree: int = 45
    ia: str = "gemini"  # "gemini" ou "claude"

# Schémas Pydantic
class ExerciseResponse(BaseModel):
    id: Optional[int] = None
    exercise_id: str
    name_fr: str
    name_en: str
    body_part: str
    target_muscle: str
    equipment: Optional[str]
    instructions_fr: List[str]
    gif_url: Optional[str]
    gif_local_path: Optional[str]

    class Config:
        from_attributes = True

class DailyWorkoutResponse(BaseModel):
    date: str
    cycle: str
    muscles: List[str]
    exercises: List[dict]
    total_exercises: int


class ExerciceResponse(BaseModel):
    nom: str
    series: int
    repetitions: str
    repos_secondes: int
    conseils: Optional[str] = None


class ProgrammeResponse(BaseModel):
    id: int
    groupes: str
    objectif: str
    niveau: str
    duree: int
    ia: str
    exercices: List[ExerciceResponse]
    created_at: datetime.datetime

    class Config:
        from_attributes = True


@app.get("/")
def root():
    """Point d'entrée de l'API"""
    return {
        "message": "🔥 Iron Pulse API v3.0 - ExerciseDB Integration",
        "version": "3.0.0",
        "endpoints": {
            "create_programme": "POST /programme",
            "get_programme": "GET /programme/{id}",
            "list_programmes": "GET /programmes",
            "health": "GET /health",
            "sync_exercises": "POST /exercises/sync",
        }
    }


@app.get("/health")
def health():
    """Health check"""
    return {"status": "healthy", "service": "Iron Pulse API"}


@app.post("/programme", response_model=ProgrammeResponse)
def creer_programme(request: ProgrammeRequest, db: Session = Depends(get_db)):
    """
    Crée un nouveau programme d'entraînement

    Args:
        request: Configuration du programme (groupes, objectif, niveau, durée, IA)
        db: Session de base de données

    Returns:
        Programme créé avec tous les exercices
    """
    try:
        # Générer le programme avec l'IA choisie
        programme_json = generer_programme(
            groupes=request.groupes,
            objectif=request.objectif,
            niveau=request.niveau,
            duree=request.duree,
            ia=request.ia
        )

        # Sauvegarder en base
        programme = Programme(
            groupes=request.groupes,
            contenu=programme_json,
            ia=request.ia,
            created_at=datetime.datetime.now()
        )

        db.add(programme)
        db.commit()
        db.refresh(programme)

        # Retourner le programme formaté
        return ProgrammeResponse(
            id=programme.id,
            groupes=programme.groupes,
            objectif=programme_json.get("objectif", request.objectif),
            niveau=programme_json.get("niveau", request.niveau),
            duree=programme_json.get("duree", request.duree),
            ia=programme.ia,
            exercices=[ExerciceResponse(**ex) for ex in programme_json["exercices"]],
            created_at=programme.created_at
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erreur lors de la génération: {str(e)}")


@app.get("/programme/{programme_id}", response_model=ProgrammeResponse)
def get_programme(programme_id: int, db: Session = Depends(get_db)):
    """
    Récupère un programme par son ID

    Args:
        programme_id: ID du programme
        db: Session de base de données

    Returns:
        Programme complet
    """
    programme = db.query(Programme).filter(Programme.id == programme_id).first()

    if not programme:
        raise HTTPException(status_code=404, detail="Programme non trouvé")

    contenu = programme.contenu

    return ProgrammeResponse(
        id=programme.id,
        groupes=programme.groupes,
        objectif=contenu.get("objectif", "non spécifié"),
        niveau=contenu.get("niveau", "non spécifié"),
        duree=contenu.get("duree", 0),
        ia=programme.ia,
        exercices=[ExerciceResponse(**ex) for ex in contenu["exercices"]],
        created_at=programme.created_at
    )


@app.get("/programmes")
def list_programmes(
        skip: int = 0,
        limit: int = 10,
        groupes: Optional[str] = None,
        ia: Optional[str] = None,
        db: Session = Depends(get_db)
):
    """
    Liste tous les programmes avec filtres optionnels

    Args:
        skip: Nombre de programmes à passer
        limit: Nombre maximum de programmes à retourner
        groupes: Filtrer par groupes musculaires
        ia: Filtrer par IA utilisée ("gemini" ou "claude")
        db: Session de base de données

    Returns:
        Liste de programmes
    """
    query = db.query(Programme)

    if groupes:
        query = query.filter(Programme.groupes.contains(groupes))

    if ia:
        query = query.filter(Programme.ia == ia)

    programmes = query.order_by(Programme.created_at.desc()).offset(skip).limit(limit).all()

    return {
        "total": query.count(),
        "skip": skip,
        "limit": limit,
        "programmes": [
            {
                "id": p.id,
                "groupes": p.groupes,
                "ia": p.ia,
                "nb_exercices": len(p.contenu.get("exercices", [])),
                "created_at": p.created_at
            }
            for p in programmes
        ]
    }


@app.delete("/programme/{programme_id}")
def delete_programme(programme_id: int, db: Session = Depends(get_db)):
    """
    Supprime un programme

    Args:
        programme_id: ID du programme à supprimer
        db: Session de base de données

    Returns:
        Message de confirmation
    """
    programme = db.query(Programme).filter(Programme.id == programme_id).first()

    if not programme:
        raise HTTPException(status_code=404, detail="Programme non trouvé")

    db.delete(programme)
    db.commit()

    return {"message": f"Programme {programme_id} supprimé avec succès"}


@app.post("/exercises/sync/{muscle}")
def sync_exercises_for_muscle(
        muscle: str,
        limit: int = 4,
        db: Session = Depends(get_db)
):
    """
    Synchronise les exercices depuis ExerciseDB pour un muscle donné
    Télécharge les GIFs et traduit en français

    Args:
        muscle: Nom du muscle en français (dos, biceps, pectoraux, etc.)
        limit: Nombre d'exercices à récupérer (défaut: 4)
        db: Session de base de données

    Returns:
        Liste des exercices synchronisés
    """
    try:
        exercises = get_exercises_by_muscle(muscle, limit)

        if not exercises:
            raise HTTPException(status_code=404, detail=f"Aucun exercice trouvé pour {muscle}")

        saved_exercises = []
        for ex in exercises:
            # Vérifier si l'exercice existe déjà
            existing = db.query(Exercise).filter(
                Exercise.exercise_id == ex['exercise_id']
            ).first()

            if existing:
                # Mettre à jour
                existing.name_fr = ex['name_fr']
                existing.gif_local_path = ex.get('gif_local_path', '')
                existing.updated_at = datetime.datetime.now()
                db.commit()
                saved_exercises.append(existing)
            else:
                # Créer nouveau
                new_exercise = Exercise(
                    exercise_id=ex['exercise_id'],
                    name_en=ex['name_en'],
                    name_fr=ex['name_fr'],
                    body_part=ex['body_part'],
                    target_muscle=ex['target_muscle'],
                    equipment=ex.get('equipment', ''),
                    instructions_en='\n'.join(ex.get('instructions_en', [])),
                    instructions_fr='\n'.join(ex.get('instructions_fr', [])),
                    gif_url=ex.get('gif_url', ''),
                    gif_local_path=ex.get('gif_local_path', ''),
                    created_at=datetime.datetime.now(),
                    updated_at=datetime.datetime.now()
                )
                db.add(new_exercise)
                db.commit()
                db.refresh(new_exercise)
                saved_exercises.append(new_exercise)

        return {
            "message": f"{len(saved_exercises)} exercices synchronisés pour {muscle}",
            "exercises": [
                {
                    "id": ex.id,
                    "name_fr": ex.name_fr,
                    "target_muscle": ex.target_muscle,
                    'gif_url': ex.gif_url,
                }
                for ex in saved_exercises
            ]
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erreur de synchronisation: {str(e)}")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=9000)