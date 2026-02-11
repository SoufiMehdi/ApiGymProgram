import os
import requests
from datetime import datetime
from typing import List, Dict
from deep_translator import GoogleTranslator
from dotenv import load_dotenv

load_dotenv()

# Configuration ExerciseDB
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


def get_exercises_by_muscle(muscle: str, limit: int = 4, equipment_filter: List[str] = None) -> List[Dict]:
    """
    Récupère des exercices depuis ExerciseDB API pour un muscle donné
    AVEC RANDOMISATION et FILTRAGE PAR ÉQUIPEMENT

    Args:
        muscle: Nom du muscle en français (ex: "dos", "biceps")
        limit: Nombre d'exercices à récupérer (défaut: 4)
        equipment_filter: Liste d'équipements autorisés (ex: ["barbell", "dumbbell", "cable"])

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
        url = f"{EXERCISEDB_BASE_URL}/exercises/search"
        params = {
            "search": muscle_en
        }

        print(f"🔍 Recherche exercices pour: {muscle} ({muscle_en})")
        print(f"   URL: {url}")
        if equipment_filter:
            print(f"   Équipements: {', '.join(equipment_filter)}")

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

        # 🎯 FILTRAGE PAR ÉQUIPEMENT si spécifié
        if equipment_filter:
            filtered_exercises = [
                ex for ex in exercises
                if ex.get("equipment", "").lower() in [eq.lower() for eq in equipment_filter]
            ]

            if filtered_exercises:
                exercises = filtered_exercises
                print(f"   Après filtrage équipement: {len(exercises)} exercices")
            else:
                print(f"   ⚠️  Aucun exercice avec l'équipement demandé, utilisation de tous")

        # 🎲 RANDOMISATION : Mélanger les exercices avant de prendre les premiers
        random.shuffle(exercises)

        # Limiter au nombre demandé APRÈS randomisation
        exercises = exercises[:limit] if exercises else []

        print(f"✅ {len(exercises)} exercices sélectionnés aléatoirement")

        # Traduire et formater
        translated_exercises = []
        for ex in exercises:
            # S'adapter à la structure de cette API
            exercise_id = ex.get("id") or ex.get("_id") or ex.get("exerciseId", "")
            name = ex.get("name", "")
            equipment = ex.get("equipment", "")

            translated = {
                "exercise_id": str(exercise_id),
                "name_en": name,
                "name_fr": translate_text(name) if name else "",
                "body_part": ex.get("bodyPart", ex.get("body_part", "")),
                "target_muscle": ex.get("target", ex.get("targetMuscle", muscle_en)),
                "equipment": equipment,
                "gif_url": ex.get("gifUrl", ex.get("gif_url", ex.get("imageUrl", ""))),
                "video_url": ex.get("videoUrl", ex.get("video_url", "")),
                "instructions_en": ex.get("instructions", []),
                "instructions_fr": [translate_text(inst) for inst in ex.get("instructions", [])] if ex.get(
                    "instructions") else [],
                "secondary_muscles": ex.get("secondaryMuscles", ex.get("secondary_muscles", []))
            }
            translated_exercises.append(translated)
            print(f"   - {translated['name_fr']} ({equipment})")

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


def get_balanced_exercises_by_muscle(muscle: str, total: int = 4) -> List[Dict]:
    """
    Récupère des exercices ÉQUILIBRÉS pour un muscle
    Exemple pour le dos: 2 barbell + 2 dumbbell

    Args:
        muscle: Nom du muscle en français
        total: Nombre total d'exercices (défaut: 4)

    Returns:
        Liste d'exercices variés en équipement
    """

    # Configuration d'équipements par muscle
    EQUIPMENT_CONFIG = {
        "dos": [
            {"equipment": ["barbell", "pull up bar"], "count": 2},  # 2 barre/barre fixe
            {"equipment": ["dumbbell", "cable"], "count": 2}  # 2 haltères/poulie
        ],
        "biceps": [
            {"equipment": ["barbell", "ez barbell"], "count": 2},  # 2 barre
            {"equipment": ["dumbbell", "cable"], "count": 2}  # 2 haltères/poulie
        ],
        "pectoraux": [
            {"equipment": ["barbell"], "count": 2},  # 2 barre
            {"equipment": ["dumbbell"], "count": 2}  # 2 haltères
        ],
        "triceps": [
            {"equipment": ["barbell", "dip"], "count": 2},  # 2 barre/dips
            {"equipment": ["dumbbell", "cable"], "count": 2}  # 2 haltères/poulie
        ],
        "jambes": [
            {"equipment": ["barbell"], "count": 2},  # 2 barre (squat, etc.)
            {"equipment": ["machine", "body weight"], "count": 2}  # 2 machine/poids du corps
        ],
        "abdos": [
            {"equipment": ["body weight"], "count": 2},  # 2 poids du corps
            {"equipment": ["cable", "medicine ball"], "count": 2}  # 2 poulie/medecine ball
        ]
    }

    # Récupérer la config pour ce muscle
    config = EQUIPMENT_CONFIG.get(muscle, [{"equipment": [], "count": total}])

    all_exercises = []

    for equipment_group in config:
        equipment_list = equipment_group["equipment"]
        count = equipment_group["count"]

        exercises = get_exercises_by_muscle(
            muscle,
            limit=count,
            equipment_filter=equipment_list if equipment_list else None
        )

        all_exercises.extend(exercises)

    return all_exercises


def download_media(url: str, filename: str, media_type: str = "gif") -> str:
    """
    Télécharge un média (GIF, JPG, MP4, etc.) depuis une URL
    L'extension est automatiquement détectée depuis l'URL

    Args:
        url: URL du média (ex: https://cdn.exercisedb.dev/media/w/images/1OBFu6DAxW.jpg)
        filename: Nom du fichier de destination SANS extension
        media_type: Type de média ("gif" ou "video") - utilisé pour le dossier

    Returns:
        Chemin local du fichier téléchargé
    """
    try:
        # Extraire l'extension depuis l'URL
        from urllib.parse import urlparse
        import os.path

        parsed_url = urlparse(url)
        # Récupérer l'extension du chemin de l'URL
        _, extension = os.path.splitext(parsed_url.path)

        # Si pas d'extension trouvée, utiliser une extension par défaut
        if not extension:
            extension = ".gif" if media_type == "gif" else ".mp4"

        # Nettoyer l'extension (enlever les paramètres de requête éventuels)
        extension = extension.split('?')[0].lower()

        print(f"🔍 Extension détectée: {extension}")

        # Créer le dossier media s'il n'existe pas
        media_folder = f"media/{media_type}s"
        os.makedirs(media_folder, exist_ok=True)

        # Ajouter l'extension au nom de fichier
        filename_with_ext = f"{filename}{extension}"

        # Télécharger le fichier
        response = requests.get(url, stream=True)
        response.raise_for_status()

        # Chemin complet
        filepath = f"{media_folder}/{filename_with_ext}"

        # Sauvegarder
        with open(filepath, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)

        print(f"✅ Média téléchargé: {filepath}")
        return filepath

    except Exception as e:
        print(f"❌ Erreur téléchargement média {url}: {e}")
        return ""


def get_daily_exercises_by_cycle(cycle_muscles: List[str]) -> List[Dict]:
    """
    Récupère 4 exercices ÉQUILIBRÉS pour chaque muscle du cycle du jour
    Exemple: Pour le dos → 2 barre/barre fixe + 2 haltères/poulie

    Args:
        cycle_muscles: Liste des muscles du cycle (ex: ["dos", "biceps"])

    Returns:
        Liste de tous les exercices avec traduction et médias
    """
    all_exercises = []

    for muscle in cycle_muscles:
        print(f"\n🔍 Récupération des exercices ÉQUILIBRÉS pour: {muscle}")
        exercises = get_balanced_exercises_by_muscle(muscle, total=4)

        # Télécharger les GIFs/images pour chaque exercice
        for ex in exercises:
            if ex.get("gif_url"):
                # Générer un nom de fichier unique SANS extension
                filename = f"{ex['exercise_id']}_{muscle}"
                local_path = download_media(ex["gif_url"], filename, "gif")
                ex["gif_local_path"] = local_path

            # Télécharger les vidéos si disponibles
            if ex.get("video_url"):
                filename = f"{ex['exercise_id']}_{muscle}"
                local_path = download_media(ex["video_url"], filename, "video")
                ex["video_local_path"] = local_path

            # Ajouter le muscle source pour référence
            ex["muscle_source"] = muscle

        all_exercises.extend(exercises)
        print(f"✅ {len(exercises)} exercices récupérés pour {muscle}")

    return all_exercises


# Définition des cycles
TRAINING_CYCLES = {
    "dos_biceps": ["dos", "biceps"],
    "pecs_triceps": ["pectoraux", "triceps"],
    "jambes_abdos": ["jambes", "abdos"]
}


def get_cycle_for_date(date: datetime) -> str:
    """
    Détermine le cycle d'entraînement pour une date donnée

    Args:
        date: Date pour laquelle déterminer le cycle

    Returns:
        Nom du cycle ("dos_biceps", "pecs_triceps", "jambes_abdos")
    """
    # Calculer le nombre de jours depuis une date de référence
    reference_date = datetime(2025, 1, 1)  # Date de départ du cycle
    days_diff = (date - reference_date).days

    # Rotation sur 3 jours
    cycle_index = days_diff % 3

    cycle_names = list(TRAINING_CYCLES.keys())
    return cycle_names[cycle_index]


def get_today_workout() -> Dict:
    """
    Récupère le programme d'entraînement du jour

    Returns:
        Dict avec le cycle, les muscles et les exercices
    """
    today = datetime.now()
    cycle_name = get_cycle_for_date(today)
    muscles = TRAINING_CYCLES[cycle_name]

    print(f"\n🗓️  Programme du {today.strftime('%d/%m/%Y')}")
    print(f"🔥 Cycle: {cycle_name.replace('_', ' ').upper()}")
    print(f"💪 Muscles: {', '.join(muscles)}")

    exercises = get_daily_exercises_by_cycle(muscles)

    return {
        "date": today.strftime("%Y-%m-%d"),
        "cycle": cycle_name,
        "muscles": muscles,
        "exercises": exercises,
        "total_exercises": len(exercises)
    }