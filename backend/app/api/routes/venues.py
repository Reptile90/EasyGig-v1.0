from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.core.database import SessionLocal
from app.models.models import Venue, VenueType, Person, PersonType
from auth import get_current_user, get_db
from backend.app.schemas.schemas import VenueUpdate


router = APIRouter(prefix="/venues", tags=["Venues"])


@router.get("/")
def get_venues(
    nome: str = None,  # type: ignore
    city_id: int = None,  # type: ignore
    tipo: VenueType = None,  # type: ignore
    db: Session = Depends(get_db)
):

    query = db.query(Venue)
    if nome:
        query = query.filter(Venue.nome.ilike(f"%{nome}%"))

    if city_id:
        query = query.join(Venue.direttore).filter(Person.city_id == city_id)

    if tipo:
        query = query.filter(Venue.tipo_sala == tipo)

    return query.all()


@router.put("/me")
def update_venue(
    update: VenueUpdate,
    db:Session=Depends(get_db),
    current_user: Person = Depends(get_current_user),
):

    # controllo se l'utente che sta cercando di modificare è un direttore artistico
    if current_user.tipo_utente != PersonType.direttoreArtistico:  # type: ignore
        raise HTTPException(
            status_code=403,
            detail="Accesso Negato, Quest'area è riservata al direttore artistico",
        )
    # controllo se tutti i dati sono presenti
    if not update.capienza and not update.tipo_sala and not update.strumentazione:
        raise HTTPException(
            status_code=400,
            detail="Errore, occorre inserire le informazioni di capiena, tipo_sala e strumentazione",
        )
    # recupero i dati della venue
    venue = db.query(Venue).filter(Venue.id_direttore == current_user.id).first()
    # se non trovo l'id lancio un errore
    if not venue:
        raise HTTPException(
            status_code=404, detail="Locale non trovato per questo direttore"
        )
    # controlli per verifica dati
    if update.capienza is not None:
        venue.capienza = update.capienza # type: ignore

    if update.tipo_sala is not None:
        venue.tipo_sala = update.tipo_sala # type: ignore

    if update.strumentazione is not None:
        venue.strumentazione = update.strumentazione # type: ignore
    #salvataggio del db
    db.commit()
    db.refresh(venue)

    return venue
