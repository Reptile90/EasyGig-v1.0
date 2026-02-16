from typing import List, Optional
from pydantic import BaseModel,EmailStr
from datetime import date, time
from app.models.models import PersonType,VenueType,OrganizationType


class UserBase(BaseModel):
    nome: str
    cognome: str
    email: EmailStr
    password: str
    privacy: bool
    telefono: str
    city_id: int
    
    # Campi opzionali per la creazione della Band
    nome_band: Optional[str] = None
    emails_soci: Optional[List[EmailStr]] = None
    
    # Campo opzionale per chi viene invitato
    token_invito: Optional[str] = None
    
class ArtistRegister(UserBase):
    nome_band: Optional[str] = None
    emails_soci: Optional[List[EmailStr]] = None
    token_invito: Optional[str] = None
    
class DirectorRegister(UserBase):
    nome_locale: str
    email_locale: EmailStr
    telefono_locale: str
    tipo_sala: VenueType
    capienza: int
    strumentazione: str

class PromoterRegister(UserBase):
    nome_organizzazione: str
    tipo_organizzazione: OrganizationType
    
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
