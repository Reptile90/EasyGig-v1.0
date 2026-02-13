from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from database import SessionLocal
# Assicurati di importare Person per poter fare il join sulla città
from models import Venue, VenueType, Person

def get_db(): #apro la connessione con il database
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

router = APIRouter(prefix="/venues", tags=["Venues"])

@router.get("/")
def get_venues(
    nome: str = None,       # type: ignore
    city_id: int = None,    # type: ignore
    tipo: VenueType = None, # type: ignore
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