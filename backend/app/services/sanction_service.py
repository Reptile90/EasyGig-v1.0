from datetime import datetime, timedelta
import asyncio  # Necessario per l'invio parallelo
# Aggiunto joinedload per efficienza
from sqlalchemy.orm import Session, joinedload
from app.models.models import Sanction, StatoAccount, StateAccountType, Booking, BookingState, SlotType, Person, Venue, Calendar, Slot
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from app.core.database import SessionLocal
from app.services.notifier import send_ban_notification, send_reminder_notification, send_strike_notification,send_unban_notification
from fastapi import Depends, HTTPException
from app.api.routes.auth import get_db,get_current_user
# funzione per calcolare la scadenza della prenotazione


def calculate_ban_duration(current_bans):
    now = datetime.now()
    if current_bans == 0:
        days_to_add = 7
    else:
        days_to_add = 14

    data_fine_ban = now + timedelta(days=days_to_add)
    return data_fine_ban

# funzione per applicare il ban


def apply_ban(db: Session, person_id: int):
    # recupero il record
    sanction_record = db.query(Sanction).filter(
        Sanction.person_id == person_id).first()
    # recupero lo stato dell'account
    stato_account = db.query(StatoAccount).filter(
        StatoAccount.person_id == person_id).first()

    # se esistono entrambe aggiorno calcolo la scadenza e aumento il ban di 1
    if sanction_record and stato_account:
        numero_ban = sanction_record.numero_ban
        scadenza = calculate_ban_duration(numero_ban)

        sanction_record.contatorestrike = 0  # type: ignore
        sanction_record.numero_ban += 1  # type: ignore
        sanction_record.data_fine_ban = scadenza  # type: ignore
        stato_account.stato = StateAccountType.congelato  # type: ignore
        stato_account.istante = datetime.now()  # type: ignore

# funzione per il controllo delle prenotazioni


async def bookings_control(db: Session):
    ora_attuale = datetime.now()

    # Carichiamo tutto l'albero delle relazioni in un'unica query
    bookings_pendenti = db.query(Booking).options(
        joinedload(Booking.slot_item)
        .joinedload(Slot.calendar_item)
        .joinedload(Calendar.venue_calendar)
        .joinedload(Venue.direttore),
        joinedload(Booking.bands_bookings)
    ).filter(
        Booking.stato_prenotazione == BookingState.pendente
    ).all()

    tasks_notifiche = []  # Lista per raccogliere le mail da inviare in parallelo

    # itero per ogni prenotazione pendente
    for booking in bookings_pendenti:
        try:
            # Recupero dati e calcolo tempistiche
            giorni_inattivita = (ora_attuale - booking.data_creazione).days
            slot = booking.slot_item
            calendario = slot.calendar_item
            direttore = calendario.venue_calendar.direttore

            # Calcolo giorni alla data dell'evento
            data_evento = calendario.data
            giorni_alla_data = (data_evento - ora_attuale.date()).days

            # LOGICA DELLO STRIKE (Giorno 5 o urgenza evento)
            if giorni_inattivita > 5 or giorni_alla_data < 4:
                booking.stato_prenotazione = BookingState.scaduta  # type: ignore
                slot.stato = SlotType.disponibile

                sanction_record = db.query(Sanction).filter(
                    Sanction.person_id == direttore.id).first()
                if sanction_record:
                    sanction_record.contatorestrike += 1  # type: ignore

                    # Controllo se scatta il BAN
                    if sanction_record.contatorestrike >= 5:  # type: ignore
                        apply_ban(db, direttore.id)
                        # Notifica Ban (aggiunta alla lista task)
                        tasks_notifiche.append(send_ban_notification(
                            direttore.email, direttore.nome, sanction_record.numero_ban))  # type: ignore
                    else:
                        # Notifica Strike semplice (aggiunta alla lista task)
                        tasks_notifiche.append(send_strike_notification(
                            direttore.email, direttore.nome, sanction_record.contatorestrike, sanction_record.numero_ban))  # type: ignore

            # LOGICA DEL PROMEMORIA
            elif giorni_inattivita in [3, 4]:
                giorni_rimanenti = 5 - giorni_inattivita
                # Recuperiamo il nome della band per rendere la mail specifica
                band_name = booking.bands_bookings.nome if booking.bands_bookings else "Artista"

                # Aggiungiamo il promemoria ai task
                tasks_notifiche.append(send_reminder_notification(
                    email_to=direttore.email,
                    director_name=direttore.nome,
                    band_name=band_name,
                    data_evento=str(data_evento),
                    giorni_rimanenti=giorni_rimanenti
                ))

        except Exception as e:
            print(f"Errore prenotazione {booking.id}: {e}")
            db.rollback()

    # Salvataggio unico per tutte le prenotazioni elaborate
    db.commit()

    # Invio parallelo di tutte le notifiche raccolte
    if tasks_notifiche:
        await asyncio.gather(*tasks_notifiche)

# schedule dell'operazione booking_controls che verrà controllata ogni 24 ore


async def run_scheduled_control():
    db = SessionLocal()
    try:
        await bookings_control(db)
    finally:
        db.close()

scheduler = AsyncIOScheduler()
scheduler.add_job(
    run_scheduled_control,
    'interval',
    hours=24,
    id='check_bookings_job',
    replace_existing=True
)
scheduler.start()


async def check_unban(db: Session):
    ora_attuale = datetime.now()
    # 1. Recuperiamo i ban scaduti caricando subito i dati della persona
    sanction_records = db.query(Sanction).options(
        joinedload(Sanction.persona_sanzionata)
    ).filter(
        Sanction.data_fine_ban != None,
        Sanction.data_fine_ban <= ora_attuale
    ).all()

    if not sanction_records:
        return

    tasks_notifiche = []

    for record in sanction_records:
        try:
            direttore = record.persona_sanzionata
            stato = db.query(StatoAccount).filter(
                StatoAccount.person_id == record.person_id).first()

            if stato:
                record.data_fine_ban = None # type: ignore
                stato.stato = StateAccountType.attivo # type: ignore
                
                # 2. Prepariamo la notifica di bentornato
                tasks_notifiche.append(
                    send_unban_notification(direttore.email, direttore.nome)
                )
        except Exception as e:
            print(f"Errore durante lo sblocco di {record.person_id}: {e}")

    try:
        db.commit()
        # 3. Inviamo tutte le mail insieme
        if tasks_notifiche:
            await asyncio.gather(*tasks_notifiche)
    except Exception as e:
        print(f"Errore nel salvataggio finale: {e}")
        db.rollback()
        
async def run_scheduled_unban():
    db = SessionLocal()
    try:
        await check_unban(db)
    finally:
        db.close()
        
        
scheduler.add_job(
    run_scheduled_unban,
    'interval',
    hours=1,
    id='hourly_unban_check'
)

async def check_account_not_frozen(
    db: Session = Depends(get_db),
    current_user: Person = Depends(get_current_user)
):
    # Recuperiamo lo stato e la sanzione
    stato_utente = db.query(StatoAccount).filter(StatoAccount.person_id == current_user.id).first()
    sanction = db.query(Sanction).filter(Sanction.person_id == current_user.id).first()

    # Se l'account è congelato, blocchiamo l'accesso
    if stato_utente and stato_utente.stato == StateAccountType.congelato: # type: ignore
        data_fine = sanction.data_fine_ban if sanction else "data da destinarsi"
        raise HTTPException(
            status_code= 403,
            detail=f"Accesso negato. Il tuo account è bloccato fino al {data_fine} per inattività nelle prenotazioni."
        )
    
    return True