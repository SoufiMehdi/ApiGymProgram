import os
from google import genai
import json
from dotenv import load_dotenv
from anthropic import Anthropic

load_dotenv()

# Clients IA
gemini_client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))
claude_client = Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY")) if os.getenv("ANTHROPIC_API_KEY") else None

def test_github_action():
    print("Testing github action")

def generer_programme_gemini(groupes: str, objectif: str = "prise de masse", niveau: str = "intermédiaire",
                             duree: int = 45):
    """
    Génère un programme d'entraînement avec Gemini

    Args:
        groupes: Groupes musculaires (ex: "dos biceps")
        objectif: "prise de masse", "sèche", "super set", etc.
        niveau: "débutant", "intermédiaire", "avancé", "expert"
        duree: Durée en minutes
    """
    prompt = f"""
Tu es un coach sportif professionnel.
Génère UNIQUEMENT un JSON valide sans aucun texte avant ou après.

Configuration :
- Groupes musculaires : {groupes}
- Objectif : {objectif}
- Niveau : {niveau}
- Durée : {duree} minutes

Structure obligatoire :
{{
  "groupes": "{groupes}",
  "objectif": "{objectif}",
  "niveau": "{niveau}",
  "duree": {duree},
  "exercices": [
    {{
      "nom": "Nom de l'exercice",
      "series": 4,
      "repetitions": "8-12",
      "repos_secondes": 90,
      "conseils": "Conseil technique court"
    }}
  ]
}}

Règles :
- Entre 5 et 8 exercices selon la durée
- Adapter séries/reps selon l'objectif :
  * Prise de masse : 3-5 séries de 6-12 reps, repos 90s
  * Sèche : 3-4 séries de 12-15 reps, repos 45-60s
  * Super set : 2 exercices enchaînés, repos 60s
  * Force : 4-6 séries de 3-6 reps, repos 120-180s
- Varier les exercices pour couvrir tous les angles du groupe musculaire
- Conseils techniques concrets et courts (max 15 mots)
- AUCUN texte hors JSON
"""

    response = gemini_client.models.generate_content(
        model="gemini-3-flash-preview",
        contents=prompt,
        config={"response_mime_type": "application/json"}
    )

    return json.loads(response.text)


def generer_programme_claude(groupes: str, objectif: str = "prise de masse", niveau: str = "intermédiaire",
                             duree: int = 45):
    """
    Génère un programme d'entraînement avec Claude

    Args:
        groupes: Groupes musculaires (ex: "dos biceps")
        objectif: "prise de masse", "sèche", "super set", etc.
        niveau: "débutant", "intermédiaire", "avancé", "expert"
        duree: Durée en minutes
    """
    if not claude_client:
        raise ValueError("Claude API key not configured")

    prompt = f"""Crée un programme d'entraînement de {duree} minutes pour {groupes}.

Configuration:
- Objectif: {objectif}
- Niveau: {niveau}
- Groupes musculaires: {groupes}

Réponds UNIQUEMENT avec un objet JSON (sans backticks markdown) dans ce format exact:
{{
  "groupes": "{groupes}",
  "objectif": "{objectif}",
  "niveau": "{niveau}",
  "duree": {duree},
  "exercices": [
    {{
      "nom": "nom de l'exercice en français",
      "series": 4,
      "repetitions": "8-12",
      "repos_secondes": 90,
      "conseils": "conseil technique court"
    }}
  ]
}}

Règles importantes:
- Entre 5 et 8 exercices adaptés aux groupes musculaires {groupes}
- Adapter séries/reps selon l'objectif ({objectif})
- Pour la prise de masse: 3-5 séries de 6-12 reps avec charges lourdes
- Pour la sèche: 3-4 séries de 12-15 reps avec tempo contrôlé
- Pour les super sets: combiner 2 exercices antagonistes
- Varier les angles et types de mouvements
- Conseils courts et pratiques (max 15 mots)
- Temps de repos adapté à l'intensité"""

    message = claude_client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=1500,
        messages=[
            {"role": "user", "content": prompt}
        ]
    )

    response_text = message.content[0].text
    clean_text = response_text.replace("```json", "").replace("```", "").strip()

    return json.loads(clean_text)


def generer_programme(groupes: str, objectif: str = "prise de masse", niveau: str = "intermédiaire", duree: int = 45,
                      ia: str = "gemini"):
    """
    Génère un programme avec l'IA choisie

    Args:
        groupes: Groupes musculaires
        objectif: Objectif d'entraînement
        niveau: Niveau de l'utilisateur
        duree: Durée en minutes
        ia: "gemini" ou "claude"

    Returns:
        dict: Programme généré avec métadonnées
    """
    if ia == "claude":
        return generer_programme_claude(groupes, objectif, niveau, duree)
    else:
        return generer_programme_gemini(groupes, objectif, niveau, duree)