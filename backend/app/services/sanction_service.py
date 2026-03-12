from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from app.models.models import Sanction, StatoAccount, StateAccountType, Booking, BookingState,SlotType
from apscheduler.schedulers.background import BackgroundScheduler
from app.core.database import SessionLocal

#funzione per calcolare la scadenza della prenotazione
def calculate_ban_duration(current_bans):
    now = datetime.now()
    if current_bans == 0:
        days_to_add = 7
    else:
        days_to_add = 14

    data_fine_ban = now + timedelta(days=days_to_add)
    return data_fine_ban

#funzione per applicare il ban
def apply_ban(db: Session, person_id: int):
    #recupero il record
    sanction_record = db.query(Sanction).filter(
        Sanction.person_id == person_id).first()
    #recupero lo stato dell'account
    stato_account = db.query(StatoAccount).filter(
        StatoAccount.person_id == person_id).first()
    #se esistono entrambe aggiorno calcolo la scadenza e aumento il ban di 1
    if sanction_record and stato_account:
        numero_ban = sanction_record.numero_ban

        scadenza = calculate_ban_duration(numero_ban)

        sanction_record.contatorestrike = 0 # type: ignore
        sanction_record.numero_ban += 1 # type: ignore
        sanction_record.data_fine_ban = scadenza # type: ignore
        stato_account.stato = StateAccountType.congelato # type: ignore
        stato_account.istante = datetime.now() # type: ignore

        db.commit()

#funzione per il controllo delle prenotazioni
def bookings_control(db: Session):
    ora_attuale = datetime.now()
    bookings_pendenti = db.query(Booking).filter(
        Booking.stato_prenotazione == BookingState.pendente).all()
    #itero per ogni prenotazione pendente
    for booking in bookings_pendenti:
        try:
            giorni_inattivita = (ora_attuale - booking.data_creazione).days
            giorni_alla_data = 999
            slot = booking.slot_item
            if slot and slot.calendar_event and slot.calendar_event.data:
                data_evento = slot.calendar_event.data
                giorni_alla_data = (data_evento - ora_attuale.date()).days
        
            # Logica dello Strike
            if giorni_inattivita > 5 or giorni_alla_data < 4:
                if slot and slot.calendar_event and slot.calendar_event.venue_calendar:
                    direttore_id = slot.calendar_event.venue_calendar.direttore_id
                    booking.stato_prenotazione = BookingState.scaduta # type: ignore
                    slot.stato = SlotType.disponibile
                    sanction_record = db.query(Sanction).filter(Sanction.person_id == direttore_id).first()
                    if sanction_record:
                        sanction_record.contatorestrike += 1 # type: ignore
                        if sanction_record.contatorestrike >= 5: # type: ignore
                            apply_ban(db, direttore_id)
                db.commit()
        except Exception as e:
            print(f"Errore durante l'elaborazione della prenotazione {booking.id}: {e}")
            db.rollback()
    
    
    
    
#schedule dell'operazione booking_controls che verrà controllata ogni 24 ore
def run_scheduled_control():
    db = SessionLocal()
    try:
        bookings_control(db)
    finally:
            db.close()
                
scheduler = BackgroundScheduler()
scheduler.add_job(run_scheduled_control,'interval',hours=24)
scheduler.start()