from fastapi import APIRouter, Depends,HTTPException
from sqlalchemy.orm import Session
from auth import get_db,get_current_user
from backend.app.models.models import Booking, PersonType, Slot, Person, BookingState, SlotType,Venue,Calendar,Band, pers_band
from backend.app.schemas.schemas import BookingReject


router = APIRouter(prefix="/bookings", tags = ["Bookings"])


@router.post("/{booking_id}/accept")
def accept_booking(
    booking_id: int,
    db:Session = Depends(get_db),
    current_user: Person = Depends(get_current_user)
):
    booking = db.query(Booking).filter(Booking.id == booking_id).first()
    
    if not booking:
        raise HTTPException(status_code=404, detail="Prenotazione non trovata")
    
    venue = db.query(Venue).join(Calendar).join(Slot).filter(Slot.id == booking.slot_id).first()
    
    if not venue or venue.direttore_id != current_user.id: # type: ignore
        raise HTTPException(status_code=403, detail="Non hai i permessi per gestire la prenotazione")
    
    if booking.stato_prenotazione != BookingState.pendente: # type: ignore
        raise HTTPException(status_code=400, detail="Questa prenotazione è già stata gestita")
    
    booking.stato_prenotazione = BookingState.accettata # type: ignore
    
    slot = db.query(Slot).filter(Slot.id == booking.slot_id).first()
    if slot: # type: ignore
        slot.stato = SlotType.occupato # type: ignore
        
    db.commit()
    return {"message": "Prenotazione accettata con successo!", "booking_id": booking_id}



@router.post("/{booking_id}/reject")
def reject_booking(
    booking_id:int,
    reject_data: BookingReject,
    db:Session = Depends(get_db),
    current_user:Person = Depends(get_current_user)
):
    booking = db.query(Booking).filter(Booking.id == booking_id).first()
    
    if not booking:
        raise HTTPException(status_code=404, detail="Prenotazione non trovata")
    
    venue = db.query(Venue).join(Calendar).join(Slot).filter(Slot.id == booking.slot_id)
    
    if not venue or venue.direttore_id != current_user.id: # type: ignore
        raise HTTPException(status_code=403, detail="Non autorizzato")
    
    if not reject_data.ragione or len(reject_data.ragione).strip()== 0: # type: ignore
        raise HTTPException(status_code=400, detail="Devi fornire un motivazione per il rifiuto")
    
    booking.stato_prenotazione = BookingState.rifiutata # type: ignore
    booking.ragione = reject_data.ragione # type: ignore
    
    slot = db.query(Slot).filter(Slot.id == booking.slot_id).first()
    if slot:
        slot.stato = SlotType.disponibile # type: ignore
        
    db.commit()
    return {"message": "Prenotazione rifiutata", "ragione": booking.ragione}



@router.get("/my-bookings")
def get_my_bookings(
    db:Session = Depends(get_db),
    current_user:Person = Depends(get_current_user)
):
    if current_user.tipo_utente != PersonType.artista: # type: ignore
        raise HTTPException(status_code=403, detail="Accesso riservato agli artisti")
    my_bookings = db.query(Booking).join(Band).join(pers_band).filter(pers_band.person_id == current_user.id).all()
    
    return my_bookings