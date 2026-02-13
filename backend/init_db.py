from database import engine
from sqlalchemy import text
import models


def init_db():
    print("--- INIZIO INIZIALIZZAZIONE DATABASE ---")

    print("1. Creazione tabelle standard (ORM)...")
    models.Base.metadata.create_all(bind=engine)
    print("   Tabelle create con successo.")

    print("2. Inserimento Trigger e Procedure (SQL)...")

    sql_commands = text("""
    /* ==============================================
       SEZIONE 3: TRIGGER STRUTTURALI (Vincoli)
       ============================================== */

    -- 3.1 ORGANIZZAZIONE (Constraint Deferrable per permettere inserimento transazionale)
    CREATE OR REPLACE FUNCTION check_org_insert_consistency() RETURNS TRIGGER AS $$
    BEGIN
        IF NOT EXISTS (SELECT 1 FROM person WHERE organization_id = NEW.id) THEN
            RAISE EXCEPTION 'L''organizzazione "%" deve avere almeno una persona associata.', NEW.nome;
        END IF;
        RETURN NULL;
    END;
    $$ LANGUAGE plpgsql;

    DROP TRIGGER IF EXISTS tr_check_org_insert ON booking_organization;
    CREATE CONSTRAINT TRIGGER tr_check_org_insert AFTER INSERT ON booking_organization DEFERRABLE INITIALLY DEFERRED FOR EACH ROW EXECUTE FUNCTION check_org_insert_consistency();

    -- 3.2 BAND
    CREATE OR REPLACE FUNCTION check_band_insert_consistency() RETURNS TRIGGER AS $$
    BEGIN
        IF NOT EXISTS (SELECT 1 FROM pers_band WHERE band_id = NEW.id) THEN
            RAISE EXCEPTION 'La band "%" deve avere almeno un membro.', NEW.nome;
        END IF;
        RETURN NULL;
    END;
    $$ LANGUAGE plpgsql;

    DROP TRIGGER IF EXISTS tr_check_band_insert ON band;
    CREATE CONSTRAINT TRIGGER tr_check_band_insert AFTER INSERT ON band DEFERRABLE INITIALLY DEFERRED FOR EACH ROW EXECUTE FUNCTION check_band_insert_consistency();

    -- 3.3 VENUE
    CREATE OR REPLACE FUNCTION check_venue_insert_consistency() RETURNS TRIGGER AS $$
    BEGIN
        IF NOT EXISTS (SELECT 1 FROM calendar WHERE venue_id = NEW.id) THEN
            RAISE NOTICE 'Attenzione: La Venue "%" è stata creata senza calendario.', NEW.nome;
            -- Non solleviamo eccezione qui per facilitare l'onboarding, ma è una best practice averlo.
        END IF;
        RETURN NULL;
    END;
    $$ LANGUAGE plpgsql;
    
    /* ==============================================
       SEZIONE 4: LOGICA DI BUSINESS (TRIGGER)
       ============================================== */

    -- Init Status (Creazione automatica Sanction e StatoAccount)
    CREATE OR REPLACE FUNCTION init_user_status() RETURNS TRIGGER AS $$
    BEGIN
        INSERT INTO sanction (contatorestrike, soglia_warning, soglia_ban, person_id) VALUES (0, 3, 5, NEW.id);
        INSERT INTO stato_account (stato, istante, person_id) VALUES ('attivo', CURRENT_TIMESTAMP, NEW.id);
        RETURN NEW;
    END;
    $$ LANGUAGE plpgsql;
    
    DROP TRIGGER IF EXISTS tr_init_person ON person;
    CREATE TRIGGER tr_init_person AFTER INSERT ON person FOR EACH ROW EXECUTE FUNCTION init_user_status();

    -- Reputazione (Calcolo media voti)
    CREATE OR REPLACE FUNCTION aggiorna_reputazione() RETURNS TRIGGER AS $$
    DECLARE v_destinatario_id INTEGER; v_nuova_media DECIMAL(3, 2);
    BEGIN
        -- Recuperiamo il destinatario dalla recensione collegata allo score
        IF (TG_OP = 'DELETE') THEN
            SELECT destinatario_id INTO v_destinatario_id FROM review WHERE id = OLD.review_id; 
        ELSE
            SELECT destinatario_id INTO v_destinatario_id FROM review WHERE id = NEW.review_id; 
        END IF;
        
        -- Calcoliamo la media
        SELECT COALESCE(AVG(s.voto), 0) INTO v_nuova_media
        FROM score s JOIN review r ON s.review_id = r.id
        WHERE r.destinatario_id = v_destinatario_id;
        
        UPDATE person SET reputazione = v_nuova_media WHERE id = v_destinatario_id;
        RETURN NULL;
    END;
    $$ LANGUAGE plpgsql;
    
    DROP TRIGGER IF EXISTS tr_aggiorna_reputazione ON score;
    CREATE TRIGGER tr_aggiorna_reputazione AFTER INSERT OR UPDATE OR DELETE ON score FOR EACH ROW EXECUTE FUNCTION aggiorna_reputazione();

    -- Ban Automatico (BEFORE UPDATE per evitare ricorsione)
    CREATE OR REPLACE FUNCTION trigger_ban_automatico() RETURNS TRIGGER AS $$
    BEGIN
        IF NEW.contatorestrike >= NEW.soglia_ban THEN
            -- Congela account
            UPDATE person SET tipo_utente = NULL WHERE id = NEW.person_id;
            INSERT INTO stato_account (stato, istante, person_id) VALUES ('congelato', CURRENT_TIMESTAMP, NEW.person_id);
            
            -- Aggiorna data ban (direttamente su NEW, senza update ricorsivo)
            NEW.data_ultimo_ban := CURRENT_TIMESTAMP;
            
            RAISE NOTICE 'Utente % bannato automaticamente per superamento soglia strike.', NEW.person_id;
        END IF;
        RETURN NEW;
    END;
    $$ LANGUAGE plpgsql;
    
    DROP TRIGGER IF EXISTS tr_check_ban_threshold ON sanction;
    CREATE TRIGGER tr_check_ban_threshold BEFORE UPDATE OF contatorestrike ON sanction FOR EACH ROW EXECUTE FUNCTION trigger_ban_automatico();

    -- Validazione Recensione
    CREATE OR REPLACE FUNCTION check_review_eligibility() RETURNS TRIGGER AS $$
    DECLARE
        v_stato_booking VARCHAR;
        v_data_fine TIME;
        v_data_evento DATE;
    BEGIN
        -- JOIN CORRETTA: booking -> slot -> calendar
        SELECT b.stato_prenotazione, c.data, s.orario_fine
        INTO v_stato_booking, v_data_evento, v_data_fine
        FROM booking b
        JOIN slot s ON b.slot_id = s.id
        JOIN calendar c ON s.calendar_id = c.id
        WHERE b.id = NEW.booking_id;
        
        IF v_stato_booking = 'annullata' THEN RETURN NEW; END IF;
        
        IF v_stato_booking = 'accettata' THEN
            -- Controllo se l'evento è finito (Data + Ora Fine)
            IF CURRENT_TIMESTAMP < (v_data_evento + v_data_fine) THEN
                RAISE EXCEPTION 'Non puoi recensire prima che l''evento sia terminato.'; 
            END IF;
            RETURN NEW;
        END IF;
        
        RAISE EXCEPTION 'Non puoi recensire una prenotazione in stato %.', v_stato_booking;
    END;
    $$ LANGUAGE plpgsql;
    
    DROP TRIGGER IF EXISTS tr_check_review_time ON review;
    CREATE TRIGGER tr_check_review_time BEFORE INSERT ON review FOR EACH ROW EXECUTE FUNCTION check_review_eligibility();

    -- Chat Automatica
    CREATE OR REPLACE FUNCTION auto_apri_chat_on_accept() RETURNS TRIGGER AS $$
    BEGIN
        IF NEW.stato_prenotazione = 'accettata' AND OLD.stato_prenotazione <> 'accettata' THEN
            -- Crea chat se non esiste già per questo booking
            IF NOT EXISTS (SELECT 1 FROM chat WHERE booking_id = NEW.id) THEN
                INSERT INTO chat (data_apertura, ultimo_messaggio, booking_id) VALUES (CURRENT_TIMESTAMP, CURRENT_TIMESTAMP, NEW.id);
            END IF;
        END IF;
        RETURN NEW;
    END;
    $$ LANGUAGE plpgsql;
    
    DROP TRIGGER IF EXISTS tr_auto_chat ON booking;
    CREATE TRIGGER tr_auto_chat AFTER UPDATE ON booking FOR EACH ROW EXECUTE FUNCTION auto_apri_chat_on_accept();


    /* ==============================================
       SEZIONE 5: PROCEDURE (OPERAZIONI)
       ============================================== */

    -- Accetta Prenotazione
    CREATE OR REPLACE PROCEDURE accetta_prenotazione(p_booking_id INTEGER) LANGUAGE plpgsql AS $$
    DECLARE v_cal_id INTEGER;
    BEGIN
        -- JOIN CORRETTA: booking -> slot -> calendar
        SELECT s.calendar_id INTO v_cal_id
        FROM booking b
        JOIN slot s ON b.slot_id = s.id
        WHERE b.id = p_booking_id;
        
        -- Decrementa slot disponibili
        UPDATE calendar SET slot_disponibili = slot_disponibili - 1
        WHERE id = v_cal_id AND slot_disponibili > 0;
        
        IF NOT FOUND THEN
            RAISE EXCEPTION 'Impossibile accettare: Slot esauriti per questa data!'; 
        END IF;
        
        UPDATE booking SET stato_prenotazione = 'accettata' WHERE id = p_booking_id;
    END;
    $$;

    -- Rifiuta Prenotazione
    CREATE OR REPLACE PROCEDURE rifiuta_prenotazione(p_booking_id INTEGER, p_ragione TEXT) LANGUAGE plpgsql AS $$
    BEGIN
        IF p_ragione IS NULL OR p_ragione = '' THEN
            RAISE EXCEPTION 'La motivazione del rifiuto è obbligatoria.';
        END IF;
        UPDATE booking SET stato_prenotazione = 'rifiutata', ragione = p_ragione WHERE id = p_booking_id;
    END;
    $$;

    -- Inserisci Recensione
    CREATE OR REPLACE PROCEDURE inserisci_recensione(p_autore INTEGER, p_destinatario INTEGER, p_desc TEXT, p_voto INTEGER, p_book INTEGER) 
    LANGUAGE plpgsql AS $$
    DECLARE v_id INTEGER;
    BEGIN
        INSERT INTO review (description, autore_id, destinatario_id, booking_id)
        VALUES (p_desc, p_autore, p_destinatario, p_book) RETURNING id INTO v_id;
        
        INSERT INTO score (voto, review_id) VALUES (p_voto, v_id);
    END;
    $$;

    -- Invia Messaggio
    CREATE OR REPLACE PROCEDURE invia_messaggio(p_chat INTEGER, p_mittente INTEGER, p_testo TEXT) LANGUAGE plpgsql AS $$
    BEGIN
        INSERT INTO message (data_invio, testo, letto, chat_id, mittente_id) 
        VALUES (CURRENT_TIMESTAMP, p_testo, FALSE, p_chat, p_mittente);
        
        UPDATE chat SET ultimo_messaggio = CURRENT_TIMESTAMP WHERE id = p_chat;
    END;
    $$;

    -- Controllo Scadenze (JOB)
    CREATE OR REPLACE PROCEDURE controlla_scadenze_prenotazioni() LANGUAGE plpgsql AS $$
    DECLARE r RECORD; v_colpevole INTEGER;
    BEGIN
        -- JOIN CORRETTA per recuperare venue_id: booking -> slot -> calendar -> venue
        FOR r IN
            SELECT b.id, c.venue_id, b.band_id, b.iniziato_da
            FROM booking b
            JOIN slot s ON b.slot_id = s.id
            JOIN calendar c ON s.calendar_id = c.id
            WHERE b.stato_prenotazione = 'pendente'
            AND b.data_creazione < (CURRENT_TIMESTAMP - INTERVAL '5 days')
        LOOP
            v_colpevole := NULL;
            
            -- Se ha iniziato l'artista, deve rispondere il Direttore del locale
            IF r.iniziato_da = 'artista' THEN
                SELECT direttore_id INTO v_colpevole FROM venue WHERE id = r.venue_id;
            
            -- Se ha iniziato il promoter, deve rispondere l'Artista (un membro della band)
            ELSIF r.iniziato_da = 'promoter' THE
                SELECT person_id INTO v_colpevole FROM pers_band WHERE band_id = r.band_id LIMIT 1;
            END IF;
            
            -- Applica Strike
            IF v_colpevole IS NOT NULL THEN
                UPDATE sanction SET contatorestrike = contatorestrike + 1 WHERE person_id = v_colpevole;
            END IF;
            
            -- Chiudi prenotazione
            UPDATE booking SET stato_prenotazione = 'scaduta', ragione = 'Timeout risposta 5gg' WHERE id = r.id;
        END LOOP;
    END;
    $$;
    """)

    # 3. Esecuzione dei comandi SQL
    with engine.connect() as conn:
        with conn.begin():  # Avvia la transazione
            print("   Esecuzione script SQL...")
            conn.execute(sql_commands)

    print("--- INIZIALIZZAZIONE COMPLETATA CON SUCCESSO ---")


if __name__ == "__main__":
    init_db()
