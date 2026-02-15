from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from fastapi_mail import ConnectionConfig, FastMail, MessageSchema, MessageType
from pydantic import EmailStr
from dotenv import load_dotenv
from sqlalchemy.orm import Session
from passlib.context import CryptContext
from database import SessionLocal
from models import Person, StateAccountType, Invitation, StateInvitation, pers_band, Band,PersonType
from schemas import UserBase,ArtistRegister,DirectorRegister,PromoterRegister
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


#ENDPOINT PER LA REGISTRAZIONE DEGLI ARTISTI
@router.post("/register/artist")
def register_artist(
    user:ArtistRegister,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    #Controllo se la mail è già presente nel db
    if db.query(Person).filter(Person.email == user.email).first():
        raise HTTPException(status_code=400, detail="Email già registrata")
    
    #Controllo se ha l'invito
    invito = None
    if user.token_invito: #Se c'è l'invito faccio una query per confrontare il token inviato.
        invito = db.query(Invitation).filter(
            Invitation.token == user.token_invito,
            Invitation.stato == StateInvitation.pending
        ).first()
        if not invito: #se dal controllo l'invito non risulta valido mando un eccezione
            raise HTTPException(status_code=409, detail="Invito non valido o scaduto")
    
    try:
        #Creo l'utente se non esiste già
        password_hash = pwd_context.hash(user.password) #salvo l'hash della password
        nuovo_utente = Person( #registro i dati dell'utente in ingresso
            nome = user.nome,
            cognome = user.cognome,
            email = user.email,
            password_hash = password_hash,
            privacy_accettata = user.privacy,
            telefono = user.telefono,
            city_id = user.city_id,
            tipo_utente = PersonType.artista
        )
        db.add(nuovo_utente)
        db.flush() #Ottengo l'ID
        
        #Nel caso voglia spedire gli inviti alla registrazione dei componenti della band
        inviti_da_spedire = []
        #CASO 1: Si unisce ad una band esistente tramite l'invito
        if invito:
            db.add(pers_band(person_id = nuovo_utente.id, band_id = invito.band_id))
            invito.stato = StateInvitation.accepted # type: ignore
            invito.person_id = nuovo_utente.id
        #CASO2: La band non esiste, viene create e si associa
        elif user.nome_band:
            nuova_band = Band(
                nome = user.nome_band,
                cachet = 0, #default
                categoria = "inedita", #default
                genere_id=1 #default
            )
            db.add(nuova_band)
            db.flush()
            
            #Associo la band l'utente
            db.add(pers_band(person_id = nuovo_utente.id, band_id = nuova_band.id))
            
            #Nel caso volesse invitare gli altri componenti
            if user.emails_soci:
                for mail in user.emails_soci:
                    token = str(uuid.uuid4())
                    db.add(Invitation(
                        email = mail,
                        token = token,
                        band_id = nuova_band.id,
                        sender_id = nuovo_utente.id
                    ))
        #Commit finale
        db.commit()
        
        #Spedisco gli inviti
        for invito in inviti_da_spedire:
            background_tasks.add_task(
                send_invitation_email,
                invito["email"],
                invito["token"],
                nuovo_utente.nome, # type: ignore
                invito["band"]
                
            )
        #messaggio di conferma
        return {"message": "Registrazione artista avvenuta con successo", "id": nuovo_utente.id}
    
    except Exception as e:
        db.rollback()
        print(f"Errore: {e}")
        raise HTTPException(status_code=500, detail="Errore durante la registrazione")
            
    
    