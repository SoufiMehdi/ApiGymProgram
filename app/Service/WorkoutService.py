"""
Service de sélection intelligente d'exercices pour éviter les répétitions
"""

from datetime import datetime, timedelta
from typing import List, Dict
from sqlalchemy.orm import Session
from sqlalchemy import func, and_
import random

from app.Models.Exercise import Exercise
from app.Models.program import Programme


def get_random_exercises_from_db(
        db: Session,
        muscle: str,
        limit: int = 4,
        avoid_recent_days: int = 7
) -> List[Exercise]:
    """
    Sélectionne des exercices aléatoires depuis la BDD
    en évitant ceux utilisés dans les derniers jours

    Args:
        db: Session de base de données
        muscle: Muscle cible (ex: "back", "biceps")
        limit: Nombre d'exercices à retourner
        avoid_recent_days: Éviter les exercices des N derniers jours

    Returns:
        Liste d'exercices
    """

    # Date limite pour éviter les répétitions
    cutoff_date = datetime.now() - timedelta(days=avoid_recent_days)

    # Récupérer tous les exercices pour ce muscle
    all_exercises = db.query(Exercise).filter(
        Exercise.target_muscle.ilike(f"%{muscle}%")
    ).all()

    if not all_exercises:
        print(f"⚠️  Aucun exercice en BDD pour {muscle}")
        return []

    # Récupérer les exercices utilisés récemment
    recent_programmes = db.query(Programme).filter(
        Programme.created_at >= cutoff_date
    ).all()

    # Extraire les IDs des exercices récents
    recent_exercise_ids = set()
    for prog in recent_programmes:
        contenu = prog.contenu
        if 'exercises' in contenu:
            for ex in contenu['exercises']:
                if 'exercise_id' in ex:
                    recent_exercise_ids.add(str(ex['exercise_id']))

    # Filtrer les exercices pour éviter les récents
    available_exercises = [
        ex for ex in all_exercises
        if str(ex.exercise_id) not in recent_exercise_ids
    ]

    # Si pas assez d'exercices disponibles, prendre tous
    if len(available_exercises) < limit:
        print(f"⚠️  Pas assez d'exercices non-récents ({len(available_exercises)}), ajout des récents")
        available_exercises = all_exercises

    # Randomiser et prendre le nombre demandé
    random.shuffle(available_exercises)
    selected = available_exercises[:limit]

    print(f"✅ {len(selected)} exercices sélectionnés pour {muscle}")
    print(f"   ({len(all_exercises)} disponibles, {len(recent_exercise_ids)} utilisés récemment)")

    return selected


def get_varied_workout(
        db: Session,
        muscles: List[str],
        exercises_per_muscle: int = 4,
        avoid_recent_days: int = 7
) -> Dict:
    """
    Génère un programme varié en évitant les répétitions

    Args:
        db: Session de base de données
        muscles: Liste des muscles à travailler
        exercises_per_muscle: Nombre d'exercices par muscle
        avoid_recent_days: Jours à éviter

    Returns:
        Programme complet avec exercices variés
    """

    all_exercises = []

    for muscle in muscles:
        # Essayer de récupérer depuis la BDD d'abord
        db_exercises = get_random_exercises_from_db(
            db,
            muscle,
            limit=exercises_per_muscle,
            avoid_recent_days=avoid_recent_days
        )

        if db_exercises:
            # Convertir les modèles en dict
            for ex in db_exercises:
                all_exercises.append({
                    "exercise_id": ex.exercise_id,
                    "name_fr": ex.name_fr,
                    "name_en": ex.name_en,
                    "target_muscle": ex.target_muscle,
                    "equipment": ex.equipment,
                    "instructions_fr": ex.instructions_fr.split('\n') if ex.instructions_fr else [],
                    "gif_local_path": ex.gif_local_path,
                    "gif_url": ex.gif_url,
                    "video_url": ex.video_url,
                    "muscle_source": muscle
                })
        else:
            print(f"⚠️  Aucun exercice en BDD pour {muscle}, il faut synchroniser d'abord")

    return {
        "exercises": all_exercises,
        "total_exercises": len(all_exercises),
        "source": "database_randomized"
    }


def get_exercise_stats(db: Session, days: int = 30) -> Dict:
    """
    Statistiques sur les exercices utilisés

    Args:
        db: Session de base de données
        days: Période en jours

    Returns:
        Statistiques
    """

    cutoff_date = datetime.now() - timedelta(days=days)

    # Compter les programmes
    total_programmes = db.query(Programme).filter(
        Programme.created_at >= cutoff_date
    ).count()

    # Compter les exercices en BDD
    total_exercises_db = db.query(Exercise).count()

    # Exercices par muscle
    exercises_by_muscle = db.query(
        Exercise.target_muscle,
        func.count(Exercise.id)
    ).group_by(Exercise.target_muscle).all()

    return {
        "total_programmes_created": total_programmes,
        "total_exercises_in_db": total_exercises_db,
        "exercises_by_muscle": {muscle: count for muscle, count in exercises_by_muscle},
        "period_days": days
    }