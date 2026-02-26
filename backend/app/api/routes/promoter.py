from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from auth import get_current_user, get_db
from backend.app.models.models import Person, PersonType
from backend.app.schemas.schemas import PromoterUpdate

router = APIRouter(prefix="/promoters", tags=["Promoters"])


@router.put("/me")
def update_promoter(
    update: PromoterUpdate,
    db: Session = Depends(get_db),
    current_user: Person = Depends(get_current_user)
):
    # Verifichiamo il ruolo
    if current_user.tipo_utente != PersonType.promoter:  # type: ignore
        raise HTTPException(status_code=403, detail="Accesso negato")
    # se non ci sono tutti i dati, lanciamo un errore
    if not any([update.nome, update.cognome, update.city_id, update.descrizione]):
        raise HTTPException(
            status_code=400, detail="Errore: inserire almeno un campo da aggiornare")
    # controlli dei dati
    if update.nome is not None:
        current_user.nome = update.nome  # type: ignore

    if update.cognome is not None:
        current_user.cognome = update.cognome  # type: ignore

    if update.city_id is not None:
        current_user.city_id = update.city_id  # type: ignore

    if update.descrizione is not None:
        current_user.descrizione = update.descrizione
    # salvataggio nel db
    db.commit()
    db.refresh(current_user)

    return current_user
