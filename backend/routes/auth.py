from fastapi import APIRouter, Depends, HTTPException
from fastapi_mail import ConnectionConfig
from dotenv import load_dotenv
from sqlalchemy.orm import Session
from passlib.context import CryptContext
from database import SessionLocal
from models import Person, StateAccountType,Invitation,StateInvitation,pers_band,Band
from schemas import UserCreate
import uuid
import os

load_dotenv()

conf = ConnectionConfig(
    MAIL_USERNAME = os.getenv('MAIL_USERNAME'), # type: ignore
    MAIL_PASSWORD = os.getenv('MAIL_PASSWORD'),# type: ignore
    MAIL_FROM = os.getenv('MAIL_FROM'),# type: ignore
    MAIL_PORT = int(os.getenv('MAIL_PORT')),# type: ignore
    MAIL_SERVER = os.getenv('MAIL_SERVER'),# type: ignore
    MAIL_FROM_NAME="EasyGIG Team",
    MAIL_STARTTLS = True, # Necessario per la porta 587
    MAIL_SSL_TLS = False,
    USE_CREDENTIALS = True,
    VALIDATE_CERTS = True
)

router = APIRouter()

#configurazione per criptare la password
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

#funzione per ottenere il db
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
        
        
@router.post("/register")
def register(user:UserCreate, db:Session = Depends(get_db)):
    invito = None
    if user.token_invito:
        invito = db.query(Invitation).filter(
            Invitation.token == user.token_invito,
            Invitation.stato == StateInvitation.pending).first()
        if not invito:
            raise HTTPException(status_code=409, detail="Errore, invito non valido o scaduto")
    
    #controllo se l'email esiste già nel db
    email_esistente = db.query(Person).filter(Person.email == user.email).first()
    if email_esistente:
        raise HTTPException(status_code=400, detail = "Email già registrata")
    
    password_encrypted = pwd_context.hash(user.password)
    
    nuovo_utente = Person(
        nome = user.nome,
        cognome = user.cognome,
        email = user.email,
        password_hash = password_encrypted,
        privacy_accettata = user.privacy,
        telefono="0000000000",
        city_id=1
        )
    db.add(nuovo_utente)
    db.commit()
    db.refresh(nuovo_utente)
    
    if invito:
        nuovo_legame = pers_band(
            person_id=nuovo_utente.id,
            band_id=invito.band_id
        )
        db.add(nuovo_legame)
        invito.stato = StateInvitation.accepted # type: ignore
        invito.person_id = nuovo_utente.id
        db.commit()

    elif user.tipo_utente == "artista" and getattr(user, 'nome_band', None):
        nuova_band = Band(
            nome=user.nome_band,
            cachet=0,
            categoria="inedita",
            genere_id=1
        )
        db.add(nuova_band)
        db.commit()
        db.refresh(nuova_band)

        legame_creatore = pers_band(person_id=nuovo_utente.id, band_id=nuova_band.id)
        db.add(legame_creatore)
        
        if getattr(user, 'emails_soci', None):
             for mail_socio in user.emails_soci: # type: ignore
                 token_unico = str(uuid.uuid4())
                 nuovo_invito = Invitation(
                     email=mail_socio,
                     token=token_unico,
                     band_id=nuova_band.id,
                     sender_id=nuovo_utente.id
                 )
                 db.add(nuovo_invito)

        db.commit()
    return {
        "message": "Registrazione avvenuta con successo",
        "id_utente": nuovo_utente.id
        }