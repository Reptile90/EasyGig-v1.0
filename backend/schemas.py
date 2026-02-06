from pydantic import BaseModel,EmailStr
from datetime import date, time

class UserCreate(BaseModel):
    nome:str
    cognome:str
    email:EmailStr
    password:str
    privacy:bool
    
    
class CalendarCreate(BaseModel):
    data:date
    ora_inizio:time
    ora_fine:time
    numero_slot:int
    
class CalendarSchema(CalendarCreate):
    id: int

    class Config:
        from_attributes = True
        
        
class SlotBooking(BaseModel):
    artista_id:int