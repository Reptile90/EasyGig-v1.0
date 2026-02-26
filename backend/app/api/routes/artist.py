from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.core.database import SessionLocal
from app.models.models import Person, Band, PersonType
from auth import get_current_user
from auth import get_db
from backend.app.schemas.schemas import ArtistUpdate

router = APIRouter(prefix="/artists", tags=["Artists"])

@router.put("/me")
def update_artist(
    update:ArtistUpdate,
    db:Session=Depends(get_db),
    current_user:Person = Depends(get_current_user)
):  #controllo l'accesso all'utente
    if current_user.tipo_utente != PersonType.artista: # type: ignore
        raise HTTPException(status_code=403, detail="Errore, Accesso negato: Area Riservata agli Artisti")
    #se non ci sono dati lancio un errore
    if not update.link_streaming and not update.file_path:
        raise HTTPException(status_code=400, detail="Errore, è necessario inserire obbligatoriamento un link o caricare un brano")
    #controlli sui dati
    if update.link_streaming:
        current_user.link_streaming = update.link_streaming # type: ignore
    
    if update.file_path:
        current_user.file_path = update.file_path # type: ignore
    #salvo nel db
    db.commit()
    db.refresh(current_user)
    return current_user
    
    
        