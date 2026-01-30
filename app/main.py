import datetime
from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional, List

from app.database import engine, get_db
from app.Models.program import Base, Programme
from app.ia import generer_programme

# Créer les tables
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="Iron Pulse API",
    description="API de génération de programmes d'entraînement avec IA",
    version="2.0.0"
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Schémas Pydantic
class ProgrammeRequest(BaseModel):
    groupes: str
    objectif: str = "prise de masse"
    niveau: str = "intermédiaire"
    duree: int = 45
    ia: str = "gemini"  # "gemini" ou "claude"


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
        "message": "🔥 Iron Pulse API v2.0",
        "endpoints": {
            "create_programme": "POST /programme",
            "get_programme": "GET /programme/{id}",
            "list_programmes": "GET /programmes",
            "health": "GET /health"
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


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)