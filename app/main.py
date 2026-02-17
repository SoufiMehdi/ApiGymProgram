import datetime
from fastapi import FastAPI, HTTPException, Depends, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional, List

from app.database import engine, get_db
from app.Models.Exercise import Base, Exercise
from app.Models.program import Programme
from app.Models.TrainingCycle import TrainingCycle
from app.Service.ExercisedbService import (
    get_today_workout,
    get_exercises_by_muscle,
    get_cycle_for_date,
    TRAINING_CYCLES
)

from app.Service.Auth import verify_api_key

# Créer les tables
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="Iron Pulse API",
    description="API de génération de programmes d'entraînement avec IA et ExerciseDB",
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


@app.get("/")
def root():
    """Point d'entrée de l'API"""
    return {
        "message": "🔥 Iron Pulse API v3.0 - ExerciseDB Integration",
        "version": "3.0.0",
        "endpoints": {
            "daily_workout": "GET /workout/today",
            "sync_exercises": "POST /exercises/sync",
            "get_exercises": "GET /exercises",
            "health": "GET /health"
        }
    }


@app.get("/health")
def health():
    """Health check"""
    return {"status": "healthy", "service": "Iron Pulse API v3.0"}


@app.get("/workout/today", response_model=DailyWorkoutResponse)
def get_daily_workout(use_db: bool = False, db: Session = Depends(get_db)):
    """
    Récupère le programme d'entraînement du jour
    Rotation automatique : dos/biceps → pecs/triceps → jambes/abdos

    Args:
        use_db: Si True, utilise les exercices en BDD avec sélection intelligente
                Si False, récupère depuis l'API ExerciseDB (par défaut)
        db: Session de base de données

    Returns:
        Programme du jour avec 4 exercices par muscle
    """
    try:
        if use_db:
            # Mode intelligent : utiliser la BDD avec anti-répétition
            from app.Service.WorkoutService import get_varied_workout
            from app.Service.ExercisedbService import get_cycle_for_date, TRAINING_CYCLES

            today = datetime.datetime.now()
            cycle_name = get_cycle_for_date(today)
            muscles = TRAINING_CYCLES[cycle_name]

            # Convertir les noms de muscles français en anglais
            muscle_mapping = {
                "dos": "back",
                "biceps": "biceps",
                "pectoraux": "chest",
                "triceps": "triceps",
                "jambes": "legs",
                "abdos": "abs"
            }
            muscles_en = [muscle_mapping.get(m, m) for m in muscles]

            workout_data = get_varied_workout(db, muscles_en, exercises_per_muscle=4)

            return {
                "date": today.strftime("%Y-%m-%d"),
                "cycle": cycle_name,
                "muscles": muscles,
                "exercises": workout_data["exercises"],
                "total_exercises": workout_data["total_exercises"]
            }
        else:
            # Mode normal : récupérer depuis l'API
            workout = get_today_workout()
            return workout
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erreur: {str(e)}")


@app.get("/workout/cycle/{date}")
def get_workout_for_date(date: str):
    """
    Récupère le cycle d'entraînement pour une date donnée

    Args:
        date: Date au format YYYY-MM-DD

    Returns:
        Informations sur le cycle du jour
    """
    try:
        target_date = datetime.datetime.strptime(date, "%Y-%m-%d")
        cycle_name = get_cycle_for_date(target_date)
        muscles = TRAINING_CYCLES[cycle_name]

        return {
            "date": date,
            "cycle": cycle_name,
            "muscles": muscles,
            "cycle_description": {
                "dos_biceps": "Jour 1: Dos et Biceps",
                "pecs_triceps": "Jour 2: Pectoraux et Triceps",
                "jambes_abdos": "Jour 3: Jambes et Abdominaux"
            }.get(cycle_name)
        }
    except ValueError:
        raise HTTPException(status_code=400, detail="Format de date invalide. Utilisez YYYY-MM-DD")


@app.post("/exercises/sync/{muscle}")
def sync_exercises_for_muscle(
        muscle: str,
        limit: int = 4,
        equipment: Optional[str] = None,
        balanced: bool = True,
        db: Session = Depends(get_db),
        auth: str = Depends(verify_api_key)
):
    """
    Synchronise les exercices depuis ExerciseDB pour un muscle donné
    Télécharge les GIFs et traduit en français

    Args:
        muscle: Nom du muscle en français (dos, biceps, pectoraux, etc.)
        limit: Nombre d'exercices à récupérer (défaut: 4)
        equipment: Filtrer par équipement (barbell, dumbbell, cable, etc.) - optionnel
        balanced: Si True, utilise la sélection équilibrée (2 barbell + 2 dumbbell)
        db: Session de base de données

    Returns:
        Liste des exercices synchronisés
    """
    try:
        from app.Service.ExercisedbService import get_balanced_exercises_by_muscle

        if balanced:
            # Mode équilibré (recommandé)
            exercises = get_balanced_exercises_by_muscle(muscle, total=limit)
        else:
            # Mode manuel avec filtre d'équipement
            equipment_list = equipment.split(',') if equipment else None
            exercises = get_exercises_by_muscle(muscle, limit, equipment_filter=equipment_list)

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
                existing.video_local_path = ex.get('video_local_path', '')
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
                    video_url=ex.get('video_url', ''),
                    video_local_path=ex.get('video_local_path', ''),
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
                    "equipment": ex.equipment,
                    "target_muscle": ex.target_muscle,
                    "image": ex.gif_url
                }
                for ex in saved_exercises
            ]
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erreur de synchronisation: {str(e)}")


@app.post("/exercises/sync-all")
def sync_all_exercises(
        db: Session = Depends(get_db),
        auth: str = Depends(verify_api_key)
):
    """
    Synchronise tous les exercices pour tous les muscles du cycle

    Returns:
        Résumé de la synchronisation
    """
    all_muscles = []
    for muscles in TRAINING_CYCLES.values():
        all_muscles.extend(muscles)

    # Supprimer les doublons
    all_muscles = list(set(all_muscles))

    results = []
    for muscle in all_muscles:
        try:
            result = sync_exercises_for_muscle(muscle, limit=4, db=db)
            results.append({
                "muscle": muscle,
                "count": len(result["exercises"]),
                "status": "success"
            })
        except Exception as e:
            results.append({
                "muscle": muscle,
                "error": str(e),
                "status": "error"
            })

    total_synced = sum(r.get("count", 0) for r in results)

    return {
        "message": f"Synchronisation terminée: {total_synced} exercices",
        "details": results
    }


@app.get("/exercises")
def list_exercises(
        muscle: Optional[str] = None,
        skip: int = 0,
        limit: int = 20,
        db: Session = Depends(get_db)
):
    """
    Liste les exercices stockés en base de données

    Args:
        muscle: Filtrer par muscle cible
        skip: Nombre à passer (pagination)
        limit: Nombre maximum à retourner
        db: Session de base de données

    Returns:
        Liste d'exercices
    """
    query = db.query(Exercise)

    if muscle:
        query = query.filter(Exercise.target_muscle.contains(muscle))

    exercises = query.offset(skip).limit(limit).all()
    total = query.count()

    return {
        "total": total,
        "skip": skip,
        "limit": limit,
        "exercises": [
            {
                "id": ex.id,
                "name_fr": ex.name_fr,
                "name_en": ex.name_en,
                "target_muscle": ex.target_muscle,
                "equipment": ex.equipment,
                "gif_local_path": ex.gif_local_path
            }
            for ex in exercises
        ]
    }


@app.get("/exercises/{exercise_id}", response_model=ExerciseResponse)
def get_exercise(exercise_id: int, db: Session = Depends(get_db)):
    """
    Récupère un exercice par son ID

    Args:
        exercise_id: ID de l'exercice
        db: Session de base de données

    Returns:
        Détails complets de l'exercice
    """
    exercise = db.query(Exercise).filter(Exercise.id == exercise_id).first()

    if not exercise:
        raise HTTPException(status_code=404, detail="Exercice non trouvé")

    return ExerciseResponse(
        id=exercise.id,
        exercise_id=exercise.exercise_id,
        name_fr=exercise.name_fr,
        name_en=exercise.name_en,
        body_part=exercise.body_part,
        target_muscle=exercise.target_muscle,
        equipment=exercise.equipment,
        instructions_fr=exercise.instructions_fr.split('\n') if exercise.instructions_fr else [],
        gif_url=exercise.gif_url,
        gif_local_path=exercise.gif_local_path
    )


@app.get("/cycles")
def get_cycles():
    """
    Retourne tous les cycles d'entraînement disponibles

    Returns:
        Liste des cycles avec leurs muscles
    """
    return {
        "cycles": TRAINING_CYCLES,
        "rotation": [
            {"day": 1, "cycle": "dos_biceps", "muscles": ["dos", "biceps"]},
            {"day": 2, "cycle": "pecs_triceps", "muscles": ["pectoraux", "triceps"]},
            {"day": 3, "cycle": "jambes_abdos", "muscles": ["jambes", "abdos"]}
        ]
    }


@app.get("/exercises/stats")
def get_stats(days: int = 30, db: Session = Depends(get_db)):
    """
    Statistiques sur les exercices

    Args:
        days: Période en jours (défaut: 30)
        db: Session de base de données

    Returns:
        Statistiques détaillées
    """
    from app.Service.WorkoutService import get_exercise_stats

    try:
        stats = get_exercise_stats(db, days)
        return stats
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erreur: {str(e)}")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)