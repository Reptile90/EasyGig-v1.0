from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.models.models import Person, PersonType, Band,pers_band
from auth import get_current_user
from auth import get_db
from backend.app.schemas.schemas import ArtistUpdate, BandUpdate

router = APIRouter(prefix="/artists", tags=["Artists"])


@router.put("/me")
def update_artist(
    update: ArtistUpdate,
    db: Session = Depends(get_db),
    current_user: Person = Depends(get_current_user)
):  # controllo l'accesso all'utente
    if current_user.tipo_utente != PersonType.artista:  # type: ignore
        raise HTTPException(
            status_code=403, detail="Errore, Accesso negato: Area Riservata agli Artisti")
    # se non ci sono dati lancio un errore
    if not update.link_streaming and not update.file_path:
        raise HTTPException(
            status_code=400, detail="Errore, è necessario inserire obbligatoriamento un link o caricare un brano")
    # controlli sui dati
    if update.link_streaming:
        current_user.link_streaming = update.link_streaming  # type: ignore

    if update.file_path:
        current_user.file_path = update.file_path  # type: ignore
    # salvo nel db
    db.commit()
    db.refresh(current_user)
    return current_user

 # Assicurati di averlo nel file schemas


router = APIRouter(prefix="/artists", tags=["Artists"])


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
        band.nome = update.nome  # type: ignore

    if update.genere_id is not None:  # type: ignore
        band.genere_id = update.genere_id  # type: ignore #

    if update.cachet is not None:  # type: ignore
        band.cachet = update.cachet  # type: ignore #

    # Salvataggio
    db.commit()
    db.refresh(band)

    return band
