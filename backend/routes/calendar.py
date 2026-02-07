from datetime import date,time, datetime,timedelta
from sqlalchemy.orm import Session
from database import SessionLocal
from fastapi import APIRouter,Depends, HTTPException
from models import Calendar,Slot,Booking, enum
from schemas import CalendarCreate,CalendarSchema,SlotBooking



router = APIRouter()

def calcolaDurataSlot(data:date, inizio:time, fine:time, slots:int):
    """
    Docstring per calcolaDurataSlot
    
    :param data: è una data
    :type data: date
    :param inizio: Orario di inizio dello slot
    :type inizio: time
    :param fine: Orario di fine dello slot
    :type fine: time
    :param slots: numero di slot inseriti dal locale
    :type slots: int
    return: è la durata di un singolo slot(timedelta)
    """
    inizio_dt:datetime = datetime.combine(data,inizio)
    fine_dt:datetime = datetime.combine(data,fine)
    durata_slots = (fine_dt-inizio_dt) / slots
    return durata_slots

def get_db(): #apro la connessione con il database
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

#Endpoint POST per la creazione di un calendario e di relativi slot "a scelta" del direttore artistico
@router.post("/", response_model = CalendarSchema)
def create_calendar(calendar_data:CalendarCreate, db:Session = Depends(get_db)):
    try:
        data = calendar_data.data
        data_inizio = calendar_data.ora_inizio
        data_fine = calendar_data.ora_fine
        slot_disponibili = calendar_data.numero_slot
        durata = calcolaDurataSlot(data,data_inizio,data_fine,slot_disponibili)
        calendar = Calendar(data=data,data_inizio=data_inizio,data_fine=data_fine,slot_disponibili=slot_disponibili)
    
        db.add(calendar)
        db.commit()
        db.refresh(calendar)
    
        attuale_dt =datetime.combine(data,data_inizio)
        for n in range(slot_disponibili):
            fine_dt = durata + attuale_dt
            slot = Slot(orario_inizio=attuale_dt,orario_fine=fine_dt,calendar_id=calendar.id)
            attuale_dt = fine_dt
            db.add(slot)
        db.commit()
    except Exception as error:
        raise HTTPException(status_code=500, detail=f"Errore: {error}")
    
    return calendar


#Enndpoint GET per recuperare tutti i calendari.
@router.get("/", response_model=list[CalendarSchema])
def get_calendars(db:Session = Depends(get_db)):
    try:
     calendar_list = db.query(Calendar).all()
    except Exception as error:
        raise HTTPException(status_code=500, detail= f"Errore: {error}")
    return calendar_list


#ENDPOINT POST per creare la prenotazione.
@router.post("/{slot_id}")
def book(slot_id:int, booking_data:SlotBooking, db:Session = Depends(get_db)):
    slot= None
    try:
        slot = db.query(Slot).filter(Slot.id==slot_id).first() #cerco lo slot
        active_booking = db.query(Booking).filter(Booking.slot_id == slot_id,Booking.stato_prenotazione.notin_(['rifiutata', 'annullata'])).first() #una prenotazione attiva in quello slot
        
    except Exception as error:
        raise HTTPException(status_code=500,detail=f"Error: {error}")
    if not slot:
        raise HTTPException(status_code=404, detail="Errore, slot non trovato")
        
    if active_booking:
        raise HTTPException(status_code=409, detail="Errore, Slot già occupato")
    data_scadenza = datetime.now() + timedelta(days=5)
    new_book = Booking(
        slot_id=slot_id,
        band_id=booking_data.artista_id,
        stato_prenotazione='pendente',
        scadenza = data_scadenza,
        message = "Richiesta di prenotazione"
        )
    try:
        db.add(new_book)
        db.commit()
        db.refresh(new_book)
    except Exception as error:
        raise HTTPException(status_code=500, detail=f"Errore: {error}")
    
    return new_book