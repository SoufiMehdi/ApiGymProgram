"""
Script de test complet pour Iron Pulse API v2.0
"""

import requests
import json
from typing import Dict, Any

API_URL = "http://localhost:8000"


def print_section(title: str):
    """Affiche un titre de section"""
    print("\n" + "=" * 80)
    print(f"  {title}")
    print("=" * 80)


def print_result(success: bool, message: str):
    """Affiche un résultat de test"""
    icon = "✅" if success else "❌"
    print(f"{icon} {message}")


def test_health():
    """Test du endpoint health"""
    print_section("TEST HEALTH CHECK")
    try:
        response = requests.get(f"{API_URL}/health")
        data = response.json()
        print_result(response.status_code == 200, f"Health check: {data}")
        return response.status_code == 200
    except Exception as e:
        print_result(False, f"Erreur: {str(e)}")
        return False


def test_root():
    """Test du endpoint root"""
    print_section("TEST ROOT ENDPOINT")
    try:
        response = requests.get(f"{API_URL}/")
        data = response.json()
        print_result(response.status_code == 200, f"Root: {data.get('message')}")
        print(f"Endpoints disponibles: {json.dumps(data.get('endpoints'), indent=2)}")
        return response.status_code == 200
    except Exception as e:
        print_result(False, f"Erreur: {str(e)}")
        return False


def create_programme(groupes: str, objectif: str, niveau: str, duree: int, ia: str) -> Dict[str, Any]:
    """Crée un programme et retourne les données"""
    print_section(f"CRÉATION PROGRAMME - {ia.upper()}")
    print(f"Groupes: {groupes} | Objectif: {objectif} | Niveau: {niveau} | Durée: {duree}min")

    try:
        response = requests.post(
            f"{API_URL}/programme",
            json={
                "groupes": groupes,
                "objectif": objectif,
                "niveau": niveau,
                "duree": duree,
                "ia": ia
            }
        )

        if response.status_code == 200:
            data = response.json()
            print_result(True, f"Programme #{data['id']} créé avec {len(data['exercices'])} exercices")
            print("\nExercices générés:")
            for i, ex in enumerate(data['exercices'], 1):
                print(f"  {i}. {ex['nom']}")
                print(f"     {ex['series']} séries × {ex['repetitions']} reps | Repos: {ex['repos_secondes']}s")
                if ex.get('conseils'):
                    print(f"     💡 {ex['conseils']}")
            return data
        else:
            error = response.json()
            print_result(False, f"Erreur {response.status_code}: {error}")
            return None
    except Exception as e:
        print_result(False, f"Erreur: {str(e)}")
        return None


def test_get_programme(programme_id: int):
    """Récupère un programme par ID"""
    print_section(f"RÉCUPÉRATION PROGRAMME #{programme_id}")

    try:
        response = requests.get(f"{API_URL}/programme/{programme_id}")

        if response.status_code == 200:
            data = response.json()
            print_result(True, f"Programme récupéré: {data['groupes']} ({data['ia']})")
            print(f"Créé le: {data['created_at']}")
            print(f"Exercices: {len(data['exercices'])}")
            return data
        else:
            print_result(False, f"Erreur {response.status_code}")
            return None
    except Exception as e:
        print_result(False, f"Erreur: {str(e)}")
        return None


def test_list_programmes():
    """Liste tous les programmes"""
    print_section("LISTE DES PROGRAMMES")

    try:
        response = requests.get(f"{API_URL}/programmes?limit=5")

        if response.status_code == 200:
            data = response.json()
            print_result(True, f"Total programmes: {data['total']}")
            print(f"\nDerniers programmes (max 5):")
            for p in data['programmes']:
                print(f"  #{p['id']} - {p['groupes']} ({p['ia']}) - {p['nb_exercices']} exercices - {p['created_at']}")
            return data
        else:
            print_result(False, f"Erreur {response.status_code}")
            return None
    except Exception as e:
        print_result(False, f"Erreur: {str(e)}")
        return None


def test_filter_programmes():
    """Test des filtres de listing"""
    print_section("TEST FILTRES")

    # Filtrer par groupes
    print("\n📋 Filtrer par 'dos':")
    try:
        response = requests.get(f"{API_URL}/programmes?groupes=dos")
        if response.status_code == 200:
            data = response.json()
            print_result(True, f"{data['total']} programmes trouvés avec 'dos'")
    except Exception as e:
        print_result(False, f"Erreur: {str(e)}")

    # Filtrer par IA
    print("\n🤖 Filtrer par IA 'gemini':")
    try:
        response = requests.get(f"{API_URL}/programmes?ia=gemini")
        if response.status_code == 200:
            data = response.json()
            print_result(True, f"{data['total']} programmes Gemini")
    except Exception as e:
        print_result(False, f"Erreur: {str(e)}")


def test_delete_programme(programme_id: int):
    """Supprime un programme"""
    print_section(f"SUPPRESSION PROGRAMME #{programme_id}")

    try:
        response = requests.delete(f"{API_URL}/programme/{programme_id}")

        if response.status_code == 200:
            data = response.json()
            print_result(True, data['message'])
            return True
        else:
            print_result(False, f"Erreur {response.status_code}")
            return False
    except Exception as e:
        print_result(False, f"Erreur: {str(e)}")
        return False


def main():
    """Fonction principale"""
    print("\n" + "🔥" * 40)
    print("  IRON PULSE API v2.0 - SUITE DE TESTS COMPLÈTE")
    print("🔥" * 40)

    # Vérifier la connexion
    if not test_health():
        print("\n❌ ERREUR: Impossible de se connecter à l'API")
        print("Assurez-vous que le serveur est lancé sur http://localhost:8000")
        return

    # Tests basiques
    test_root()

    # Demander si on veut tester la génération
    print("\n" + "=" * 80)
    print("⚠️  Les tests suivants nécessitent des clés API configurées (Gemini/Claude)")
    print("=" * 80)
    choice = input("\nVoulez-vous tester la génération de programmes? (o/n): ")

    if choice.lower() != 'o':
        print("\n✅ Tests basiques terminés avec succès!")
        return

    # Tests de création avec différentes configurations
    test_cases = [
        ("dos biceps", "prise de masse", "intermédiaire", 45, "gemini"),
        ("pectoraux triceps", "sèche", "avancé", 60, "gemini"),
        ("jambes", "force", "expert", 75, "gemini"),
    ]

    created_ids = []

    for groupes, objectif, niveau, duree, ia in test_cases:
        programme = create_programme(groupes, objectif, niveau, duree, ia)
        if programme:
            created_ids.append(programme['id'])

    # Tests de récupération
    if created_ids:
        test_get_programme(created_ids[0])

    # Test de listing
    test_list_programmes()

    # Test de filtres
    test_filter_programmes()

    # Demander si on veut supprimer les programmes de test
    if created_ids:
        print("\n" + "=" * 80)
        choice = input(f"\nVoulez-vous supprimer les {len(created_ids)} programmes de test créés? (o/n): ")
        if choice.lower() == 'o':
            for pid in created_ids:
                test_delete_programme(pid)

    print("\n" + "🔥" * 40)
    print("  ✅ TOUS LES TESTS TERMINÉS")
    print("🔥" * 40)


if __name__ == "__main__":
    main()