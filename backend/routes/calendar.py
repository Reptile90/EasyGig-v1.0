from datetime import date,time, datetime
from sqlalchemy.orm import Session
from database import SessionLocal
from fastapi import APIRouter,Depends
from models import Calendar,Slot
from schemas import CalendarCreate,CalendarSchema

router = APIRouter()

def calcolaDurataSlot(data:date, inizio:time, fine:time, slots:int):
    inizio_dt:datetime = datetime.combine(data,inizio)
    fine_dt:datetime = datetime.combine(data,fine)
    durata_slots = (fine_dt-inizio_dt) / slots
    return durata_slots

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
        
@router.post("/", response_model = CalendarSchema)
def create_calendar(calendar_data:CalendarCreate, db:Session = Depends(get_db)):
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
    
    return calendar