from database import engine
from sqlalchemy import text
import models


def init_db():
    print("--- INIZIO INIZIALIZZAZIONE DATABASE ---")

    # 1. Crea le tabelle fisiche basandosi su models.py
    print("1. Creazione tabelle standard (ORM)...")
    models.Base.metadata.create_all(bind=engine)
    print("   Tabelle create con successo.")

    # 2. Inserisce Trigger e Procedure SQL
    print("2. Inserimento Trigger e Procedure (SQL)...")

    # NOTA: Tutti i nomi delle tabelle qui sotto sono stati convertiti
    # in minuscolo (es. 'person', 'booking_organization') per combaciare con il DB.
    sql_commands = text("""
    /* ==============================================
       SEZIONE 3: TRIGGER STRUTTURALI
       ============================================== */

    -- 3.1 ORGANIZZAZIONE
    CREATE OR REPLACE FUNCTION check_org_insert_consistency() RETURNS TRIGGER AS $$
    BEGIN
        IF NOT EXISTS (SELECT 1 FROM person WHERE organization_id = NEW.id) THEN
            RAISE EXCEPTION 'L''organizzazione "%" deve avere almeno una persona associata.', NEW.nome;
        END IF;
        RETURN NULL;
    END;
    $$ LANGUAGE plpgsql;

    CREATE OR REPLACE FUNCTION check_person_delete_consistency() RETURNS TRIGGER AS $$
    DECLARE v_org_id INTEGER;
    BEGIN
        IF (TG_OP = 'DELETE') THEN v_org_id := OLD.organization_id;
        ELSIF (TG_OP = 'UPDATE') THEN v_org_id := OLD.organization_id; IF NEW.organization_id = OLD.organization_id THEN RETURN NULL; END IF;
        ELSE RETURN NULL; END IF;

        IF NOT EXISTS (SELECT 1 FROM person WHERE organization_id = v_org_id) THEN
             RAISE EXCEPTION 'L''organizzazione % rimarrebbe vuota.', v_org_id;
        END IF;
        RETURN NULL;
    END;
    $$ LANGUAGE plpgsql;

    DROP TRIGGER IF EXISTS tr_check_org_insert ON booking_organization;
    CREATE CONSTRAINT TRIGGER tr_check_org_insert AFTER INSERT ON booking_organization DEFERRABLE INITIALLY DEFERRED FOR EACH ROW EXECUTE FUNCTION check_org_insert_consistency();
    
    DROP TRIGGER IF EXISTS tr_check_org_member_delete ON person;
    CREATE CONSTRAINT TRIGGER tr_check_org_member_delete AFTER DELETE OR UPDATE ON person DEFERRABLE INITIALLY DEFERRED FOR EACH ROW EXECUTE FUNCTION check_person_delete_consistency();

    -- 3.2 BAND
    CREATE OR REPLACE FUNCTION check_band_insert_consistency() RETURNS TRIGGER AS $$
    BEGIN
        IF NOT EXISTS (SELECT 1 FROM pers_band WHERE band_id = NEW.id) THEN
            RAISE EXCEPTION 'La band "%" deve avere almeno un membro.', NEW.nome;
        END IF;
        RETURN NULL;
    END;
    $$ LANGUAGE plpgsql;

    CREATE OR REPLACE FUNCTION check_band_member_delete_consistency() RETURNS TRIGGER AS $$
    DECLARE v_band_id INTEGER;
    BEGIN
        IF (TG_OP = 'DELETE') THEN v_band_id := OLD.band_id;
        ELSIF (TG_OP = 'UPDATE') THEN v_band_id := OLD.band_id; IF NEW.band_id = OLD.band_id THEN RETURN NULL; END IF;
        ELSE RETURN NULL; END IF;

        IF NOT EXISTS (SELECT 1 FROM pers_band WHERE band_id = v_band_id) THEN
             RAISE EXCEPTION 'La band % rimarrebbe senza membri.', v_band_id;
        END IF;
        RETURN NULL;
    END;
    $$ LANGUAGE plpgsql;

    DROP TRIGGER IF EXISTS tr_check_band_insert ON band;
    CREATE CONSTRAINT TRIGGER tr_check_band_insert AFTER INSERT ON band DEFERRABLE INITIALLY DEFERRED FOR EACH ROW EXECUTE FUNCTION check_band_insert_consistency();
    
    DROP TRIGGER IF EXISTS tr_check_band_member_delete ON pers_band;
    CREATE CONSTRAINT TRIGGER tr_check_band_member_delete AFTER DELETE OR UPDATE ON pers_band DEFERRABLE INITIALLY DEFERRED FOR EACH ROW EXECUTE FUNCTION check_band_member_delete_consistency();

    -- 3.3 VENUE
    CREATE OR REPLACE FUNCTION check_venue_insert_consistency() RETURNS TRIGGER AS $$
    BEGIN
        IF NOT EXISTS (SELECT 1 FROM calendar WHERE venue_id = NEW.id) THEN
            RAISE EXCEPTION 'La Venue "%" deve avere almeno un calendario.', NEW.nome;
        END IF;
        RETURN NULL;
    END;
    $$ LANGUAGE plpgsql;

    CREATE OR REPLACE FUNCTION check_calendar_delete_consistency() RETURNS TRIGGER AS $$
    DECLARE v_venue_id INTEGER;
    BEGIN
        IF (TG_OP = 'DELETE') THEN v_venue_id := OLD.venue_id;
        ELSIF (TG_OP = 'UPDATE') THEN v_venue_id := OLD.venue_id; IF NEW.venue_id = OLD.venue_id THEN RETURN NULL; END IF;
        ELSE RETURN NULL; END IF;

        IF NOT EXISTS (SELECT 1 FROM calendar WHERE venue_id = v_venue_id) THEN
             RAISE EXCEPTION 'La Venue % rimarrebbe senza calendario.', v_venue_id;
        END IF;
        RETURN NULL;
    END;
    $$ LANGUAGE plpgsql;

    DROP TRIGGER IF EXISTS tr_check_venue_insert ON venue;
    CREATE CONSTRAINT TRIGGER tr_check_venue_insert AFTER INSERT ON venue DEFERRABLE INITIALLY DEFERRED FOR EACH ROW EXECUTE FUNCTION check_venue_insert_consistency();
    
    DROP TRIGGER IF EXISTS tr_check_calendar_delete ON calendar;
    CREATE CONSTRAINT TRIGGER tr_check_calendar_delete AFTER DELETE OR UPDATE ON calendar DEFERRABLE INITIALLY DEFERRED FOR EACH ROW EXECUTE FUNCTION check_calendar_delete_consistency();


    /* ==============================================
       SEZIONE 4: LOGICA DI BUSINESS (TRIGGER)
       ============================================== */

    -- Init Status
    CREATE OR REPLACE FUNCTION init_user_status() RETURNS TRIGGER AS $$
    BEGIN
        INSERT INTO sanction (contatorestrike, soglia_warning, soglia_ban, person_id) VALUES (0, 3, 5, NEW.id);
        INSERT INTO stato_account (stato, istante, person_id) VALUES ('attivo', CURRENT_TIMESTAMP, NEW.id);
        RETURN NEW;
    END;
    $$ LANGUAGE plpgsql;
    
    DROP TRIGGER IF EXISTS tr_init_person ON person;
    CREATE TRIGGER tr_init_person AFTER INSERT ON person FOR EACH ROW EXECUTE FUNCTION init_user_status();

    -- Reputazione
    CREATE OR REPLACE FUNCTION aggiorna_reputazione() RETURNS TRIGGER AS $$
    DECLARE v_destinatario_id INTEGER; v_nuova_media DECIMAL(3, 2);
    BEGIN
        IF (TG_OP = 'DELETE') THEN SELECT destinatario_id INTO v_destinatario_id FROM review WHERE id = OLD.review_id; -- Corretto riferimento ID
        ELSE SELECT destinatario_id INTO v_destinatario_id FROM review WHERE id = NEW.review_id; END IF;
        
        SELECT COALESCE(AVG(s.voto), 0) INTO v_nuova_media FROM score s JOIN review r ON s.review_id = r.id WHERE r.destinatario_id = v_destinatario_id;
        UPDATE person SET reputazione = v_nuova_media WHERE id = v_destinatario_id;
        RETURN NULL;
    END;
    $$ LANGUAGE plpgsql;
    
    DROP TRIGGER IF EXISTS tr_aggiorna_reputazione ON score;
    CREATE TRIGGER tr_aggiorna_reputazione AFTER INSERT OR UPDATE OR DELETE ON score FOR EACH ROW EXECUTE FUNCTION aggiorna_reputazione();

    -- Ban Automatico
    CREATE OR REPLACE FUNCTION trigger_ban_automatico() RETURNS TRIGGER AS $$
    BEGIN
        IF NEW.contatorestrike >= NEW.soglia_ban THEN
            UPDATE person SET tipo_utente = NULL WHERE id = NEW.person_id;
            INSERT INTO stato_account (stato, istante, person_id) VALUES ('congelato', CURRENT_TIMESTAMP, NEW.person_id);
            UPDATE sanction SET data_ultimo_ban = CURRENT_TIMESTAMP WHERE id = NEW.id;
            RAISE NOTICE 'Utente % bannato automaticamente.', NEW.person_id;
        END IF;
        RETURN NEW;
    END;
    $$ LANGUAGE plpgsql;
    
    DROP TRIGGER IF EXISTS tr_check_ban_threshold ON sanction;
    CREATE TRIGGER tr_check_ban_threshold AFTER UPDATE OF contatorestrike ON sanction FOR EACH ROW EXECUTE FUNCTION trigger_ban_automatico();

    -- Validazione Recensione
    CREATE OR REPLACE FUNCTION check_review_eligibility() RETURNS TRIGGER AS $$
    DECLARE v_stato_booking VARCHAR; v_data_fine TIME; v_data_evento DATE; -- BookingState trattato come varchar per semplicità
    BEGIN
        SELECT b.stato_prenotazione, c.data, c.data_fine INTO v_stato_booking, v_data_evento, v_data_fine
        FROM booking b
        JOIN calendar c ON b.calendar_id = c.id
        WHERE b.id = NEW.booking_id;
        
        IF v_stato_booking = 'annullata' THEN RETURN NEW; END IF;
        IF v_stato_booking = 'accettata' THEN
            IF CURRENT_TIMESTAMP < (v_data_evento + v_data_fine) THEN RAISE EXCEPTION 'Evento non ancora terminato.'; END IF;
            RETURN NEW;
        END IF;
        RAISE EXCEPTION 'Non puoi recensire in stato %.', v_stato_booking;
    END;
    $$ LANGUAGE plpgsql;
    
    DROP TRIGGER IF EXISTS tr_check_review_time ON review;
    CREATE TRIGGER tr_check_review_time BEFORE INSERT ON review FOR EACH ROW EXECUTE FUNCTION check_review_eligibility();

    -- Chat Automatica
    CREATE OR REPLACE FUNCTION auto_apri_chat_on_accept() RETURNS TRIGGER AS $$
    BEGIN
        IF NEW.stato_prenotazione = 'accettata' AND OLD.stato_prenotazione <> 'accettata' THEN
            INSERT INTO chat (data_apertura, ultimo_messaggio, booking_id) VALUES (CURRENT_TIMESTAMP, CURRENT_TIMESTAMP, NEW.id);
        END IF;
        RETURN NEW;
    END;
    $$ LANGUAGE plpgsql;
    
    DROP TRIGGER IF EXISTS tr_auto_chat ON booking;
    CREATE TRIGGER tr_auto_chat AFTER UPDATE ON booking FOR EACH ROW EXECUTE FUNCTION auto_apri_chat_on_accept();


    /* ==============================================
       SEZIONE 5: PROCEDURE (OPERAZIONI)
       ============================================== */

    CREATE OR REPLACE PROCEDURE accetta_prenotazione(p_booking_id INTEGER) LANGUAGE plpgsql AS $$
    DECLARE v_cal_id INTEGER;
    BEGIN
        SELECT calendar_id INTO v_cal_id FROM booking WHERE id = p_booking_id;
        
        UPDATE calendar SET slot_disponibili = slot_disponibili - 1 WHERE id = v_cal_id AND slot_disponibili > 0;
        IF NOT FOUND THEN RAISE EXCEPTION 'Slot esauriti!'; END IF;
        
        UPDATE booking SET stato_prenotazione = 'accettata' WHERE id = p_booking_id;
    END;
    $$;

    CREATE OR REPLACE PROCEDURE rifiuta_prenotazione(p_booking_id INTEGER, p_ragione TEXT) LANGUAGE plpgsql AS $$
    BEGIN
        IF p_ragione IS NULL OR p_ragione = '' THEN RAISE EXCEPTION 'Motivazione obbligatoria.'; END IF;
        UPDATE booking SET stato_prenotazione = 'rifiutata', ragione = p_ragione WHERE id = p_booking_id;
    END;
    $$;

    DROP PROCEDURE IF EXISTS inserisci_recensione(integer,integer,text,integer,integer);

CREATE OR REPLACE PROCEDURE inserisci_recensione(p_autore INTEGER, p_destinatario INTEGER, p_desc TEXT, p_voto INTEGER, p_book INTEGER) 
LANGUAGE plpgsql AS $$
DECLARE v_id INTEGER;
BEGIN
    INSERT INTO review (description, autore_id, destinatario_id, booking_id)
    VALUES (p_desc, p_autore, p_destinatario, p_book) RETURNING id INTO v_id;
    INSERT INTO score (voto, review_id) VALUES (p_voto, v_id);
END;
$$;

   DROP PROCEDURE IF EXISTS invia_messaggio(INTEGER, INTEGER, TEXT);

CREATE OR REPLACE PROCEDURE invia_messaggio(p_chat INTEGER, p_mittente INTEGER, p_testo TEXT) LANGUAGE plpgsql AS $$
BEGIN
    INSERT INTO message (data_invio, testo, letto, chat_id, mittente_id) VALUES (CURRENT_TIMESTAMP, p_testo, FALSE, p_chat, p_mittente);
    UPDATE chat SET ultimo_messaggio = CURRENT_TIMESTAMP WHERE id = p_chat;
END;
$$;

    CREATE OR REPLACE PROCEDURE controlla_scadenze_prenotazioni() LANGUAGE plpgsql AS $$
    DECLARE r RECORD; v_colpevole INTEGER;
    BEGIN
        FOR r IN SELECT b.id, b.venue_id, b.band_id, b.iniziato_da FROM booking b WHERE b.stato_prenotazione = 'pendente' AND b.data_creazione < (CURRENT_TIMESTAMP - INTERVAL '5 days') LOOP
            v_colpevole := NULL;
            IF r.iniziato_da = 'artista' THEN SELECT direttore_id INTO v_colpevole FROM venue WHERE id = r.venue_id;
            ELSIF r.iniziato_da = 'promoter' THEN SELECT person_id INTO v_colpevole FROM pers_band WHERE band_id = r.band_id LIMIT 1; END IF;
            
            IF v_colpevole IS NOT NULL THEN UPDATE sanction SET contatorestrike = contatorestrike + 1 WHERE person_id = v_colpevole; END IF;
            UPDATE booking SET stato_prenotazione = 'scaduta', ragione = 'Timeout 5gg' WHERE id = r.id;
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
