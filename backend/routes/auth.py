from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from passlib.context import CryptContext
from database import SessionLocal
from models import Person, StateAccountType
from schemas import UserCreate

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
    return {
        "message": "Registrazione avvenuta con successo",
        "id_utente": nuovo_utente.id
        }