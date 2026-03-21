from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func
from sqlalchemy.orm import Session
from datetime import datetime
from app.models.models import Booking, Review, Score, BookingState, Slot, Person
from app.api.routes.auth import get_current_user, get_db
from app.schemas.schemas import ReviewCreate


router = APIRouter(prefix="/reviews", tags=["Reviews"])

def update_reputation_score(recensito_id:int, db:Session):
    media = db.query(func.avg(Score.voto)).join(Review).filter(
        Review.recensito_id == recensito_id
    ).scalar()
    
    if media is not None:
        
        persona = db.query(Person).filter(Person.id == recensito_id).first()
        if persona:
            persona.reputazione = round(float(media),2) # type: ignore
            
            db.commit()


@router.post("/")
def write_reviews(
        review_data: ReviewCreate,
        db: Session = Depends(get_db),
        current_user=Depends(get_current_user)
):
    
    booking = db.query(Booking).filter(Booking.id == review_data.booking_id).first()
    if not booking:
        raise HTTPException(status_code=404, detail="Prenotazione non trovata")
    fine_evento = datetime.combine(booking.slot.data, booking.slot.ora_fine)
    
    if datetime.now() < fine_evento and booking.stato != BookingState.annullata:
        raise HTTPException(
            status_code=400,
            detail="Non puoi ancora recensire: L'evento non è terminato e non è stato annullato"
        )
        
    direttore_id = booking.slot.venue.direttore_id
    autore_booking_id = booking.user_id
    
    if current_user.id == autore_booking_id:
        recensito_id = direttore_id
    elif current_user.id == direttore_id:
        recensito_id = autore_booking_id
    else:
        raise HTTPException(status_code=403, detail="Non fai parte di questa prenotazione")
        
        
    exist = db.query(Review).filter(
        Review.booking_id == booking.id,
        Review.recensore_id == current_user.id
    ).first()
    if exist:
        raise HTTPException(status_code=400, detail=" Hai già lasciato una recensione per questo evento")
    
    new_review = Review(
        testo = review_data.testo,
        booking_id = booking.id,
        recensore_id = current_user.id,
        recensito_id = recensito_id # type: ignore
    )
    db.add(new_review)
    db.flush()
    
    try:
        nuova_review = Review(
            testo=review_data.testo,
            booking_id=booking.id,
            recensore_id=current_user.id,
            recensito_id=recensito_id
        )
        db.add(nuova_review)
        db.flush() # Otteniamo l'ID per lo Score

        nuovo_voto = Score(
            voto=review_data.voto,
            review_id=nuova_review.id
        )
        db.add(nuovo_voto)
        db.commit()

        # 6. Aggiornamento dinamico della reputazione
        update_reputation_score(recensito_id, db)

        return {"status": "success", "message": "Recensione inviata e reputazione aggiornata"}
    
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail="Errore durante il salvataggio della recensione")

