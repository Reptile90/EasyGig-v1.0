from fastapi_mail import ConnectionConfig, FastMail, MessageSchema, MessageType
import os

conf = ConnectionConfig(
    MAIL_USERNAME=str(os.getenv('MAIL_USERNAME', '')),
    MAIL_PASSWORD=str(os.getenv('MAIL_PASSWORD', '')), # type: ignore
    MAIL_FROM=str(os.getenv('MAIL_FROM', '')),
    MAIL_PORT=int(str(os.getenv('MAIL_PORT', '587'))),
    MAIL_SERVER=str(os.getenv('MAIL_SERVER', '')),
    MAIL_FROM_NAME="EasyGIG Team",
    MAIL_STARTTLS=True,
    MAIL_SSL_TLS=False,
    USE_CREDENTIALS=True,
    VALIDATE_CERTS=True
)
#funzione per calcolare quanti ban ha e rilasciare il risultato nell'html
def calculate_ban_duration(current_bans:int):
    rules = {
        0:7,
        "default":14
    }
    days_to_add = rules.get(current_bans,rules["default"]) # type: ignore
    return days_to_add


async def send_mail(subject:str, recipient:str, body_html:str):
    
    message = MessageSchema(
        subject=subject,
        recipients=[recipient], # type: ignore
        body=body_html,
        subtype=MessageType.html
    )
    fm = FastMail(conf)
    await fm.send_message(message)
    
    
async def send_strike_notification(email_to:str, director_name:str, strike_count:int,current_bans:int):
    subject = "Avviso di Strike! - EasyGIG"
    html = f"""
    <html>
        <body>
            <h2>Ciao {director_name},</h2>
            <p>Ti informiamo che ti è stato assegnato uno <b>strike</b> per inattività.</p>
            <p><b>Motivazione:</b> Non hai risposto a una richiesta di prenotazione entro i 5 giorni previsti.</p>
            <p>Attualmente il tuo totale è di <b>{strike_count}/5</b> strike.</p>
            <hr>
            <p><small>Ricorda: al raggiungimento del 5° strike, il tuo account verrà sospeso per {calculate_ban_duration(current_bans)} giorni.</small></p>
        </body>
    </html>
    """
    await send_mail(subject,email_to,html)
    
    
async def send_ban_notification(email_to:str, director_name:str, current_bans:int):
    subject = "Avviso di Ban - EasyGIG"
    html = f"""
    <html>
        <body>
            <h2>Ciao {director_name},</h2>
            <p>Ti informiamo che ti è stato assegnato un <b>ban</b>.</p>
            <p><b>Motivazione:</b> Hai raggiunto la soglia massima di strike</p>
            <hr>
            <p><small>Ricorda: il tuo account verrà sospeso per {calculate_ban_duration(current_bans)} giorni.</small></p>
        </body>
    </html>
    """
    await send_mail(subject, email_to,html)
    
    
async def send_reminder_notification(
    email_to:str,
    director_name:str,
    band_name:str,
    data_evento:str,
    giorni_rimanenti:int
):
    subject = f"Promemoria: Una prenotazione scade tra {giorni_rimanenti} giorni!"
    html = f"""
    <html>
        <body>
            <h2>Ciao {director_name},</h2>
            <p>Hai una richiesta di prenotazione in sospeso che richiede la tua attenzione.</p>
            <ul>
                <li><b>Band:</b> {band_name}</li>
                <li><b>Data Evento:</b> {data_evento}</li>
            </ul>
            <p>Ti restano <b>{giorni_rimanenti} giorni</b> per rispondere prima che la richiesta scada e ti venga assegnato uno <b>strike</b> automatico.</p>
            <p>Accedi subito a EasyGIG per accettare o rifiutare la prenotazione.</p>
            <hr>
            <p><small>Questa è una notifica automatica di cortesia per aiutarti a gestire il tuo locale al meglio.</small></p>
        </body>
    </html>
    """
    await send_mail(subject, email_to,html)
    