import os
import requests
from datetime import datetime
from typing import List, Dict
from deep_translator import GoogleTranslator
from dotenv import load_dotenv

load_dotenv()

EXERCISEDB_API_KEY = os.getenv("EXERCISEDB_API_KEY")
EXERCISEDB_BASE_URL = os.getenv("EXERCISEDB_BASE_URL")
EXERCISEDB_HOST = os.getenv("EXERCISEDB_HOST")

# Mapping des muscles pour l'API ExerciseDB
MUSCLE_MAPPING = {
    # Dos
    "dos": "back",
    "dorsaux": "lats",

    # Bras
    "biceps": "biceps",
    "triceps": "triceps",
    "avant-bras": "forearms",
    "avantbras": "forearms",

    # Pectoraux
    "pecs": "chest",
    "pectoraux": "chest",
    "poitrine": "chest",

    # Jambes
    "jambes": "legs",
    "quadriceps": "quads",
    "quads": "quads",
    "ischio": "hamstrings",
    "ischios": "hamstrings",
    "ischios-jambiers": "hamstrings",
    "mollets": "calves",
    "fessiers": "glutes",

    # Core
    "abdos": "abs",
    "abdominals": "abs",
    "abdominaux": "abs",

    # Épaules
    "epaules": "shoulders",
    "épaules": "shoulders",
    "deltoïdes": "shoulders",
    "deltoides": "shoulders",

    # Autres
    "trapèzes": "traps",
    "trapezes": "traps",
    "cou": "neck",
    "cardio": "cardio"
}

# Traducteur
translator = GoogleTranslator(source='en', target='fr')


def translate_text(text: str) -> str:
    """
    Traduit un texte de l'anglais vers le français

    Args:
        text: Texte à traduire

    Returns:
        Texte traduit
    """
    try:
        if not text:
            return ""
        # Limite de caractères pour Google Translate gratuit
        if len(text) > 5000:
            # Diviser en morceaux
            chunks = [text[i:i + 4000] for i in range(0, len(text), 4000)]
            translated = [translator.translate(chunk) for chunk in chunks]
            return " ".join(translated)
        return translator.translate(text)
    except Exception as e:
        print(f"Erreur de traduction: {e}")
        return text  # Retourner le texte original en cas d'erreur


def get_exercises_by_muscle(muscle: str, limit: int = 4) -> List[Dict]:
    """
    Récupère des exercices depuis ExerciseDB API pour un muscle donné
    AVEC RANDOMISATION pour avoir des exercices différents à chaque appel

    Args:
        muscle: Nom du muscle en français (ex: "dos", "biceps")
        limit: Nombre d'exercices à récupérer (défaut: 4)

    Returns:
        Liste d'exercices avec traduction française
    """
    import random

    # Convertir le muscle en anglais
    muscle_en = MUSCLE_MAPPING.get(muscle.lower(), muscle.lower())

    headers = {
        "x-rapidapi-key": EXERCISEDB_API_KEY,
        "x-rapidapi-host": EXERCISEDB_HOST
    }

    try:
        # Utiliser l'endpoint de recherche
        url = f"{EXERCISEDB_BASE_URL}/exercises"
        params = {
            "bodyParts": muscle_en,
            "equipments": "DUMBBELL"
        }

        print(f"🔍 Recherche exercices pour: {muscle} ({muscle_en})")
        print(f"   URL: {url}")

        response = requests.get(url, headers=headers, params=params)
        response.raise_for_status()

        data = response.json()

        # L'API retourne probablement un objet avec une clé "exercises" ou "data"
        if isinstance(data, dict):
            exercises = data.get('exercises', data.get('data', []))
        else:
            exercises = data

        if not exercises:
            print(f"⚠️  Aucun exercice trouvé pour {muscle}")
            return []

        print(f"📊 {len(exercises)} exercices disponibles au total")

        # 🎲 RANDOMISATION : Mélanger les exercices avant de prendre les premiers
        random.shuffle(exercises)

        # Limiter au nombre demandé APRÈS randomisation
        exercises = exercises[:limit] if exercises else []
        print(exercises)
        print(f"✅ {len(exercises)} exercices sélectionnés aléatoirement")

        # Traduire et formater
        translated_exercises = []
        for ex in exercises:
            # S'adapter à la structure de cette API
            exercise_id = ex.get("id") or ex.get("_id") or ex.get("exerciseId", "")
            name = ex.get("name", "")

            translated = {
                "exercise_id": str(exercise_id),
                "name_en": name,
                "name_fr": translate_text(name) if name else "",
                "body_part": ex.get("bodyPart", ex.get("body_part", "")),
                "target_muscle": ex.get("target", ex.get("targetMuscle", muscle_en)),
                "equipment": ex.get("equipment", ""),
                "gif_url": ex.get("gifUrl", ex.get("gif_url", ex.get("imageUrl", ""))),
                "video_url": ex.get("videoUrl", ex.get("video_url", "")),
                "instructions_en": ex.get("instructions", []),
                "instructions_fr": [translate_text(inst) for inst in ex.get("instructions", [])] if ex.get(
                    "instructions") else [],
                "secondary_muscles": ex.get("secondaryMuscles", ex.get("secondary_muscles", []))
            }
            translated_exercises.append(translated)
            print(f"   - {translated['name_fr']}")

        return translated_exercises

    except requests.exceptions.RequestException as e:
        print(f"❌ Erreur API ExerciseDB: {e}")
        if hasattr(e, 'response') and e.response is not None:
            print(f"   Status: {e.response.status_code}")
            print(f"   Body: {e.response.text[:500]}")
        return []
    except Exception as e:
        print(f"❌ Erreur lors de la récupération des exercices: {e}")
        import traceback
        traceback.print_exc()
        return []