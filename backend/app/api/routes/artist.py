from typing import Optional

from fastapi import APIRouter, Depends, HTTPException,Query
from sqlalchemy import or_
from sqlalchemy.orm import Session
from app.models.models import Person, PersonType, Band,pers_band,Genre,City
from app.api.routes.auth import get_current_user,get_db
from app.schemas.schemas import ArtistUpdate, BandUpdate

router = APIRouter(prefix="/artists", tags=["Artists"])


@router.put("/me")
def update_artist(
    update: ArtistUpdate,
    db: Session = Depends(get_db),
    current_user: Person = Depends(get_current_user)
):  # controllo l'accesso all'utente
    if current_user.tipo_utente != PersonType.artista: # type: ignore
        raise HTTPException(
            status_code=403, detail="Errore, Accesso negato: Area Riservata agli Artisti")
    # se non ci sono dati lancio un errore
    if not update.link_streaming and not update.file_path:
        raise HTTPException(
            status_code=400, detail="Errore, è necessario inserire obbligatoriamento un link o caricare un brano")
    # controlli sui dati
    if update.link_streaming:
        current_user.link_streaming = update.link_streaming # type: ignore

    if update.file_path:
        current_user.file_path = update.file_path # type: ignore
    # salvo nel db
    db.commit()
    db.refresh(current_user)
    return current_user



@router.put("/me/band")
def update_artist_band(
    current_band_name: str,
    update: BandUpdate,
    db: Session = Depends(get_db),
    current_user: Person = Depends(get_current_user)
):
    #  Verifichiamo che sia un artista
    if current_user.tipo_utente != PersonType.artista: # type: ignore
        raise HTTPException(
            status_code=403, detail="Solo gli artisti possono gestire una band")

    #  Cerchiamo la band filtrando per nome e appartenenza dell'utente
    # Uniamo la tabella Band con pers_band per controllare il collegamento
    band = db.query(Band).join(pers_band).filter(
        Band.nome == current_band_name,
        pers_band.person_id == current_user.id
    ).first()

    if not band:
        raise HTTPException(
            status_code=404,
            detail=f"Nessuna band chiamata '{current_band_name}' associata al tuo profilo"
        )

    # Aggiornamento dei campi se presenti nell'oggetto 'update'
    if update.nome is not None:
        band.nome = update.nome # type: ignore

    if update.genere_id is not None: # type: ignore
        band.genere_id = update.genere_id # type: ignore

    if update.cachet is not None: # type: ignore
        band.cachet = update.cachet # type: ignore

    # Salvataggio
    db.commit()
    db.refresh(band)

    return band


@router.get("/artists")
def search_artists(
    artist:Optional[str] = Query(None, description="Nome artista o band"),
    genere_id:Optional[int] = Query(None, description="ID del genere musicale"),
    citta: Optional[str] = Query(None, description="Nome della città"),
    categoria:Optional[str] = Query(None, description="inedita, tribute Band, cover Band"),
    db:Session = Depends(get_db)

):
    # Base query per le Band
    query_band = db.query(Band).join(Genre)
    
    #Filtri per le Band
    if artist:
        query_band = query_band.filter(Band.nome.ilike(f"%{artist}%"))
    if genere_id:
        query_band = query_band.filter(Band.genere_id == genere_id)
    if categoria:
        query_band = query_band.filter(Band.categoria == categoria)
        
    if citta:
        query_band = query_band.join(Band.band_list).join(Person).join(City).filter(City.nome.ilike(f"%{citta}%"))
        
    results_bands = query_band.all()
    
    query_artists = db.query(Person).filter(Person.tipo_utente == PersonType.artista)
    if artist:
        query_artists = query_artists.filter(or_(Person.nome.ilike(f"%{artist}%"), Person.cognome.ilike(f"%{artist}%")))
    if genere_id:
        query_artists = query_artists.filter(Person.genere_id == genere_id)
    if citta:
        query_artists = query_artists.join(City).filter(City.nome.ilike(f"%{citta}%"))

    results_artists = query_artists.all()

    return {
        "bands": results_bands,
        "solo_artists": results_artists
    }