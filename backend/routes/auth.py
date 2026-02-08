from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from fastapi_mail import ConnectionConfig, FastMail, MessageSchema, MessageType
from pydantic import EmailStr
from dotenv import load_dotenv
from sqlalchemy.orm import Session
from passlib.context import CryptContext
from database import SessionLocal
from models import Person, StateAccountType, Invitation, StateInvitation, pers_band, Band
from schemas import UserCreate
import uuid
import os

load_dotenv()

conf = ConnectionConfig(
    MAIL_USERNAME=os.getenv('MAIL_USERNAME'),  # type: ignore
    MAIL_PASSWORD=os.getenv('MAIL_PASSWORD'),  # type: ignore
    MAIL_FROM=os.getenv('MAIL_FROM'),  # type: ignore
    MAIL_PORT=int(os.getenv('MAIL_PORT')),  # type: ignore
    MAIL_SERVER=os.getenv('MAIL_SERVER'),  # type: ignore
    MAIL_FROM_NAME="EasyGIG Team",
    MAIL_STARTTLS=True,
    MAIL_SSL_TLS=False,
    USE_CREDENTIALS=True,
    VALIDATE_CERTS=True
)

router = APIRouter()

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


async def send_invitation_email(email_to: EmailStr, token: str, sender_name: str, band_name: str):
    url = f"http://127.0.0.1:8000/register?token_invito={token}"

    html = f"""
    <html>
        <body>
            <p>Ciao!</p>
            <p><strong>{sender_name}</strong> ti ha invitato a unirti alla band <strong>{band_name}</strong> su EasyGIG!</p>
            <p>Per accettare e registrarti, clicca sul link qui sotto:</p>
            <a href="{url}">Unisciti alla Band</a>
        </body>
    </html>
    """

    message = MessageSchema(
        subject=f"Invito per la band {band_name}",
        recipients=[email_to],  # type: ignore
        body=html,
        subtype=MessageType.html
    )

    fm = FastMail(conf)
    await fm.send_message(message)


@router.post("/register")
def register(user: UserCreate, background_tasks: BackgroundTasks,  db: Session = Depends(get_db)):
    invito = None
    if user.token_invito:
        invito = db.query(Invitation).filter(
            Invitation.token == user.token_invito,
            Invitation.stato == StateInvitation.pending).first()
        if not invito:
            raise HTTPException(
                status_code=409, detail="Errore, invito non valido o scaduto")

    email_esistente = db.query(Person).filter(
        Person.email == user.email).first()
    if email_esistente:
        raise HTTPException(status_code=400, detail="Email già registrata")
    try:
        password_encrypted = pwd_context.hash(user.password)
        nuovo_utente = Person(
            nome=user.nome,
            cognome=user.cognome,
            email=user.email,
            password_hash=password_encrypted,
            privacy_accettata=user.privacy,
            telefono="0000000000",
            city_id=1,
            tipo_utente=user.tipo_utente
        )
        db.add(nuovo_utente)
        db.commit()
        db.refresh(nuovo_utente)

        inviti_da_spedire = []

        if invito:
            nuovo_legame = pers_band(
                person_id=nuovo_utente.id, band_id=invito.band_id)
            db.add(nuovo_legame)
            invito.stato = StateInvitation.accepted  # type: ignore
            invito.person_id = nuovo_utente.id

        elif user.tipo_utente == "artista" and getattr(user, 'nome_band', None):
            nuova_band = Band(nome=user.nome_band, cachet=0,
                              categoria="inedita", genere_id=1)
            db.add(nuova_band)
            db.flush()

            db.add(pers_band(person_id=nuovo_utente.id, band_id=nuova_band.id))

            if getattr(user, 'emails_soci', None):
                for mail_socio in user.emails_soci:  # type: ignore
                    token_unico = str(uuid.uuid4())
                    db.add(Invitation(
                        email=mail_socio, token=token_unico,
                        band_id=nuova_band.id, sender_id=nuovo_utente.id
                    ))
                    inviti_da_spedire.append(
                        {"email": mail_socio, "token": token_unico, "band": nuova_band.nome})

        db.commit()

        for inv in inviti_da_spedire:
            background_tasks.add_task(
                send_invitation_email,
                inv["email"],
                inv["token"],
                nuovo_utente.nome,  # type: ignore
                inv["band"]
            )

        return {"message": "Registrazione avvenuta con successo", "id_utente": nuovo_utente.id}

    except Exception as e:
        db.rollback()
        print(f"Errore registrazione: {e}")
        raise HTTPException(
            status_code=500, detail="Errore interno durante il salvataggio dei dati")
