from typing import List, Optional
from pydantic import BaseModel,EmailStr
from datetime import date, time
from models import PersonType


class UserCreate(BaseModel):
    nome: str
    cognome: str
    email: EmailStr
    password: str
    privacy: bool
    tipo_utente: PersonType
    
    # Campi opzionali per la creazione della Band
    nome_band: Optional[str] = None
    emails_soci: Optional[List[EmailStr]] = None
    
    # Campo opzionale per chi viene invitato
    token_invito: Optional[str] = None
    
    
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