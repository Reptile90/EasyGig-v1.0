from fastapi import FastAPI, Depends, HTTPException
from sqlalchemy.orm import Session
from database import SessionLocal
from models import Person

app = FastAPI()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@app.get("/")
def read_root():
    return {"message":"Benvenuto in EasyGIG v 1.0"}


@app.get("/users")
def get_users(db:Session = Depends(get_db)):
    users = db.query(Person).all()
    results = []
    for u in users:
        results.append({
            "id": u.id,
            "nome_completo": f"{u.nome} {u.cognome}",
            "citta": u.city.nome,
            "organizzazione": u.organization.nome if u.organization else "Nessuna",
            "tipo": u.tipo_utente
        })
        
        return results