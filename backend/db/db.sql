BEGIN TRANSACTION;

/* ==============================================
   SEZIONE 1: DOMINI E TIPI
   ============================================== */

CREATE DOMAIN IntGEZ AS INTEGER CHECK (VALUE >= 0);
CREATE DOMAIN IntGZ AS INTEGER CHECK (VALUE > 0);
CREATE DOMAIN PhoneNumber AS VARCHAR(20) CHECK(VALUE ~ '^(\+39|0039)?[\s-]?((3\d{2})|([0]\d{1,4}))[\s-]?\d{6,7}$');
CREATE DOMAIN Email AS VARCHAR(254) CHECK (VALUE ~ '^[a-zA-Z0-9.!#$%&''*+/=?^_`{|}~-]+@[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?(?:\.[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?)*$');
CREATE DOMAIN PasswordHash AS VARCHAR(128) CHECK (length(VALUE) >= 8);
CREATE DOMAIN UrlGenerico AS VARCHAR(500) CHECK (VALUE ~ '^https?://[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}(/.*)?$');
CREATE DOMAIN Votazione as INTEGER CHECK(VALUE BETWEEN 0 AND 5);

CREATE TYPE PersonType as ENUM('artista', 'promoter', 'direttoreArtistico');
CREATE TYPE BandCategory as ENUM('inedita', 'tributeBand', 'coverBand');
CREATE TYPE OrganizationType as ENUM('agenzia', 'crew', 'collettivo', 'individuale');
CREATE TYPE VenueType as ENUM('inPiedi', 'platea', 'tavoli', 'misto');
CREATE TYPE BookingState as ENUM('pendente', 'accettata', 'rifiutata', 'scaduta', 'annullata');
CREATE TYPE SlotType as ENUM('disponibile', 'inTrattativa', 'occupato');
CREATE TYPE StateAccountType as ENUM('attivo', 'warning', 'congelato');

/* ==============================================
   SEZIONE 2: TABELLE
   ============================================== */

-- Geografica
CREATE TABLE Nation(nome VARCHAR(100) PRIMARY KEY);
CREATE TABLE Region(nome VARCHAR(100) NOT NULL, nazione VARCHAR(100) NOT NULL, PRIMARY KEY (nome,nazione), FOREIGN KEY (nazione) REFERENCES Nation(nome));
CREATE TABLE City(id SERIAL PRIMARY KEY, nome VARCHAR(100) NOT NULL, regione VARCHAR(100) NOT NULL, nazione VARCHAR(100) NOT NULL, UNIQUE (nome,regione,nazione), FOREIGN KEY (regione,nazione) REFERENCES Region(nome,nazione));
CREATE TABLE Address(id SERIAL PRIMARY KEY, via VARCHAR NOT NULL, civico VARCHAR NOT NULL, cap VARCHAR NOT NULL, citta_id INTEGER NOT NULL, UNIQUE(via,civico,citta_id), FOREIGN KEY(citta_id) REFERENCES City(id) ON UPDATE CASCADE);

-- Supporto
CREATE TABLE Genre(id SERIAL PRIMARY KEY, nome VARCHAR(200) NOT NULL);
CREATE TABLE BookingOrganization(id SERIAL PRIMARY KEY, nome VARCHAR(200) NOT NULL, storico_eventi TEXT, tipo_booking OrganizationType NOT NULL);

-- Profili
CREATE TABLE Person(
  id SERIAL PRIMARY KEY,
  nome VARCHAR(100) NOT NULL,
  cognome VARCHAR(100) NOT NULL,
  telefono PhoneNumber NOT NULL,
  email Email NOT NULL,
  password_hash PasswordHash NOT NULL,
  link_streaming UrlGenerico,
  file_path VARCHAR(500),
  tipo_utente PersonType,
  city_id INTEGER NOT NULL REFERENCES City(id),
  genere_id INTEGER NOT NULL REFERENCES Genre(id),
  organization_id INTEGER NOT NULL REFERENCES BookingOrganization(id),
  reputazione DECIMAL(3, 2) DEFAULT 0.00,
  CONSTRAINT link_o_file_obbligatorio CHECK (
    (tipo_utente <> 'artista') OR ((link_streaming IS NOT NULL) OR (file_path IS NOT NULL))
  )
);

CREATE TABLE Band(
  id SERIAL PRIMARY KEY,
  nome VARCHAR(100) NOT NULL,
  cachet IntGEZ NOT NULL,
  trattabile BOOLEAN NOT NULL DEFAULT FALSE,
  categoria BandCategory NOT NULL
);

CREATE TABLE pers_band(
    person_id INTEGER NOT NULL REFERENCES Person(id) ON DELETE CASCADE,
    band_id INTEGER NOT NULL REFERENCES Band(id) ON DELETE CASCADE,
    PRIMARY KEY(person_id, band_id)
);

CREATE TABLE Venue(
  id SERIAL PRIMARY KEY,
  nome VARCHAR NOT NULL,
  email Email NOT NULL,
  telefono PhoneNumber NOT NULL,
  tipo_sala VenueType NOT NULL,
  capienza IntGZ NOT NULL,
  strumentazione TEXT NOT NULL,
  direttore_id INTEGER NOT NULL,
  UNIQUE(email,telefono),
  CONSTRAINT fk_direttore FOREIGN KEY (direttore_id) REFERENCES Person(id) ON DELETE RESTRICT
);

CREATE TABLE Photo(
  id SERIAL PRIMARY KEY,
  nome VARCHAR(100) NOT NULL,
  source VARCHAR(254) NOT NULL,
  venue_id INTEGER NOT NULL REFERENCES Venue(id) ON DELETE CASCADE
);

-- Calendario e Booking
CREATE TABLE Calendar(
  id SERIAL PRIMARY KEY,
  slot_disponibili IntGZ NOT NULL,
  data DATE NOT NULL,
  data_inizio TIME NOT NULL,
  data_fine TIME NOT NULL,
  venue_id INTEGER NOT NULL REFERENCES Venue(id),
  CONSTRAINT fk_venue FOREIGN KEY (venue_id) REFERENCES Venue(id) ON DELETE CASCADE
);

CREATE TABLE Booking(
  id SERIAL PRIMARY KEY,
  data_creazione TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  message TEXT NOT NULL,
  scadenza TIMESTAMP NOT NULL,
  stato_prenotazione BookingState NOT NULL,
  ragione TEXT,
  iniziato_da PersonType NOT NULL DEFAULT 'artista',
  band_id INTEGER NOT NULL REFERENCES Band(id),
  venue_id INTEGER NOT NULL REFERENCES Venue(id),
  calendar_id INTEGER NOT NULL REFERENCES Calendar(id),
  CONSTRAINT ragione_obbligatoria_annullata CHECK ((stato_prenotazione <> 'annullata') OR (ragione IS NOT NULL))
);

-- Tabella mantenuta su richiesta, anche se ridondante
CREATE TABLE book_cal(
  booking_id INTEGER NOT NULL,
  calendar_id INTEGER NOT NULL,
  PRIMARY KEY(booking_id, calendar_id),
  FOREIGN KEY(booking_id) REFERENCES Booking(id),
  FOREIGN KEY(calendar_id) REFERENCES Calendar(id)
);

-- Comunicazione e Feedback
CREATE TABLE Chat(
  id SERIAL PRIMARY KEY,
  data_apertura TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  ultimo_messaggio TIMESTAMP,
  booking_id INTEGER NOT NULL REFERENCES Booking(id)
);

CREATE TABLE Message(
  id SERIAL PRIMARY KEY,
  data_invio TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  testo TEXT NOT NULL,
  letto BOOLEAN DEFAULT FALSE,
  chat_id INTEGER NOT NULL REFERENCES Chat(id) ON DELETE CASCADE,
  mittente_id INTEGER NOT NULL REFERENCES Person(id)
);

CREATE TABLE Review(
  id SERIAL PRIMARY KEY,
  data_creazione TIMESTAMP NOT NULL DEFAULT CURRENT_DATE,
  description TEXT NOT NULL,
  autore_id INTEGER NOT NULL,
  destinatario_id INTEGER NOT NULL,
  booking_id INTEGER NOT NULL REFERENCES Booking(id) ON DELETE CASCADE,
  CONSTRAINT fk_autore FOREIGN KEY (autore_id) REFERENCES Person(id) ON DELETE CASCADE,
  CONSTRAINT fk_destinatario FOREIGN KEY (destinatario_id) REFERENCES Person(id) ON DELETE CASCADE,
  CONSTRAINT no_auto_recensione CHECK (autore_id <> destinatario_id),
  CONSTRAINT una_recensione_per_booking UNIQUE (booking_id, autore_id)
);

CREATE TABLE Score(
  id SERIAL PRIMARY KEY,
  data_creazione TIMESTAMP NOT NULL DEFAULT CURRENT_DATE,
  voto Votazione NOT NULL,
  id_recensione INTEGER NOT NULL,
  CONSTRAINT fk_recensione FOREIGN KEY (id_recensione) REFERENCES Review(id)
);

-- Sanzioni
CREATE TABLE Sanction(
  id SERIAL PRIMARY KEY,
  contatoreStrike IntGEZ NOT NULL,
  soglia_warning IntGZ NOT NULL,
  soglia_ban IntGZ NOT NULL,
  person_id INTEGER NOT NULL REFERENCES Person(id),
  data_ultimo_ban TIMESTAMP
);

CREATE TABLE StatoAccount(
  id SERIAL PRIMARY KEY,
  stato StateAccountType NOT NULL,
  istante TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  person_id INTEGER NOT NULL REFERENCES Person(id)
);


/* ==============================================
   SEZIONE 3: TRIGGER STRUTTURALI (INCLUSIONE)
   ============================================== */

-- 3.1 ORGANIZZAZIONE (1..*)
CREATE OR REPLACE FUNCTION check_org_insert_consistency() RETURNS TRIGGER AS $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM Person WHERE organization_id = NEW.id) THEN
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

    IF NOT EXISTS (SELECT 1 FROM Person WHERE organization_id = v_org_id) THEN
         RAISE EXCEPTION 'L''organizzazione % rimarrebbe vuota.', v_org_id;
    END IF;
    RETURN NULL;
END;
$$ LANGUAGE plpgsql;

CREATE CONSTRAINT TRIGGER tr_check_org_insert AFTER INSERT ON BookingOrganization DEFERRABLE INITIALLY DEFERRED FOR EACH ROW EXECUTE FUNCTION check_org_insert_consistency();
CREATE CONSTRAINT TRIGGER tr_check_org_member_delete AFTER DELETE OR UPDATE ON Person DEFERRABLE INITIALLY DEFERRED FOR EACH ROW EXECUTE FUNCTION check_person_delete_consistency();

-- 3.2 BAND (1..*)
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

CREATE CONSTRAINT TRIGGER tr_check_band_insert AFTER INSERT ON Band DEFERRABLE INITIALLY DEFERRED FOR EACH ROW EXECUTE FUNCTION check_band_insert_consistency();
CREATE CONSTRAINT TRIGGER tr_check_band_member_delete AFTER DELETE OR UPDATE ON pers_band DEFERRABLE INITIALLY DEFERRED FOR EACH ROW EXECUTE FUNCTION check_band_member_delete_consistency();

-- 3.3 VENUE (1..*)
CREATE OR REPLACE FUNCTION check_venue_insert_consistency() RETURNS TRIGGER AS $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM Calendar WHERE venue_id = NEW.id) THEN
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

    IF NOT EXISTS (SELECT 1 FROM Calendar WHERE venue_id = v_venue_id) THEN
         RAISE EXCEPTION 'La Venue % rimarrebbe senza calendario.', v_venue_id;
    END IF;
    RETURN NULL;
END;
$$ LANGUAGE plpgsql;

CREATE CONSTRAINT TRIGGER tr_check_venue_insert AFTER INSERT ON Venue DEFERRABLE INITIALLY DEFERRED FOR EACH ROW EXECUTE FUNCTION check_venue_insert_consistency();
CREATE CONSTRAINT TRIGGER tr_check_calendar_delete AFTER DELETE OR UPDATE ON Calendar DEFERRABLE INITIALLY DEFERRED FOR EACH ROW EXECUTE FUNCTION check_calendar_delete_consistency();


/* ==============================================
   SEZIONE 4: LOGICA DI BUSINESS (TRIGGER)
   ============================================== */

-- Init Status
CREATE OR REPLACE FUNCTION init_user_status() RETURNS TRIGGER AS $$
BEGIN
    INSERT INTO Sanction (contatoreStrike, soglia_warning, soglia_ban, person_id) VALUES (0, 3, 5, NEW.id);
    INSERT INTO StatoAccount (stato, istante, person_id) VALUES ('attivo', CURRENT_TIMESTAMP, NEW.id);
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;
CREATE TRIGGER tr_init_person AFTER INSERT ON Person FOR EACH ROW EXECUTE FUNCTION init_user_status();

-- Reputazione
CREATE OR REPLACE FUNCTION aggiorna_reputazione() RETURNS TRIGGER AS $$
DECLARE v_destinatario_id INTEGER; v_nuova_media DECIMAL(3, 2);
BEGIN
    IF (TG_OP = 'DELETE') THEN SELECT destinatario_id INTO v_destinatario_id FROM Review WHERE id = OLD.id_recensione;
    ELSE SELECT destinatario_id INTO v_destinatario_id FROM Review WHERE id = NEW.id_recensione; END IF;
    SELECT COALESCE(AVG(s.voto), 0) INTO v_nuova_media FROM Score s JOIN Review r ON s.id_recensione = r.id WHERE r.destinatario_id = v_destinatario_id;
    UPDATE Person SET reputazione = v_nuova_media WHERE id = v_destinatario_id;
    RETURN NULL;
END;
$$ LANGUAGE plpgsql;
CREATE TRIGGER tr_aggiorna_reputazione AFTER INSERT OR UPDATE OR DELETE ON Score FOR EACH ROW EXECUTE FUNCTION aggiorna_reputazione();

-- Ban Automatico
CREATE OR REPLACE FUNCTION trigger_ban_automatico() RETURNS TRIGGER AS $$
BEGIN
    IF NEW.contatoreStrike >= NEW.soglia_ban THEN
        UPDATE Person SET tipo_utente = NULL WHERE id = NEW.person_id;
        INSERT INTO StatoAccount (stato, istante, person_id) VALUES ('congelato', CURRENT_TIMESTAMP, NEW.person_id);
        UPDATE Sanction SET data_ultimo_ban = CURRENT_TIMESTAMP WHERE id = NEW.id;
        RAISE NOTICE 'Utente % bannato automaticamente.', NEW.person_id;
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;
CREATE TRIGGER tr_check_ban_threshold AFTER UPDATE OF contatoreStrike ON Sanction FOR EACH ROW EXECUTE FUNCTION trigger_ban_automatico();

-- Validazione Recensione
-- MODIFICA: Aggiornato per usare Booking.calendar_id invece di book_cal
CREATE OR REPLACE FUNCTION check_review_eligibility() RETURNS TRIGGER AS $$
DECLARE v_stato_booking BookingState; v_data_fine TIME; v_data_evento DATE;
BEGIN
    -- Join diretto con Calendar grazie alla nuova FK su Booking
    SELECT b.stato_prenotazione, c.data, c.data_fine INTO v_stato_booking, v_data_evento, v_data_fine
    FROM Booking b 
    JOIN Calendar c ON b.calendar_id = c.id 
    WHERE b.id = NEW.booking_id;
    
    IF v_stato_booking = 'annullata' THEN RETURN NEW; END IF;
    IF v_stato_booking = 'accettata' THEN
        IF CURRENT_TIMESTAMP < (v_data_evento + v_data_fine) THEN RAISE EXCEPTION 'Evento non ancora terminato.'; END IF;
        RETURN NEW;
    END IF;
    RAISE EXCEPTION 'Non puoi recensire in stato %.', v_stato_booking;
END;
$$ LANGUAGE plpgsql;
CREATE TRIGGER tr_check_review_time BEFORE INSERT ON Review FOR EACH ROW EXECUTE FUNCTION check_review_eligibility();

-- Chat Automatica
CREATE OR REPLACE FUNCTION auto_apri_chat_on_accept() RETURNS TRIGGER AS $$
BEGIN
    IF NEW.stato_prenotazione = 'accettata' AND OLD.stato_prenotazione <> 'accettata' THEN
        INSERT INTO Chat (data_apertura, ultimo_messaggio, booking_id) VALUES (CURRENT_TIMESTAMP, CURRENT_TIMESTAMP, NEW.id);
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;
CREATE TRIGGER tr_auto_chat AFTER UPDATE ON Booking FOR EACH ROW EXECUTE FUNCTION auto_apri_chat_on_accept();


/* ==============================================
   SEZIONE 5: PROCEDURE (OPERAZIONI)
   ============================================== */

-- MODIFICA: Aggiornato per usare Booking.calendar_id
CREATE OR REPLACE PROCEDURE accetta_prenotazione(p_booking_id INTEGER) LANGUAGE plpgsql AS $$
DECLARE v_cal_id INTEGER;
BEGIN
    -- Lettura diretta dalla tabella Booking
    SELECT calendar_id INTO v_cal_id FROM Booking WHERE id = p_booking_id;
    
    -- Logica decremento slot
    UPDATE Calendar SET slot_disponibili = slot_disponibili - 1 WHERE id = v_cal_id AND slot_disponibili > 0;
    IF NOT FOUND THEN RAISE EXCEPTION 'Slot esauriti!'; END IF;
    
    UPDATE Booking SET stato_prenotazione = 'accettata' WHERE id = p_booking_id;
END;
$$;

CREATE OR REPLACE PROCEDURE rifiuta_prenotazione(p_booking_id INTEGER, p_ragione TEXT) LANGUAGE plpgsql AS $$
BEGIN
    IF p_ragione IS NULL OR p_ragione = '' THEN RAISE EXCEPTION 'Motivazione obbligatoria.'; END IF;
    UPDATE Booking SET stato_prenotazione = 'rifiutata', ragione = p_ragione WHERE id = p_booking_id;
END;
$$;

CREATE OR REPLACE PROCEDURE inserisci_recensione(p_autore INTEGER, p_destinatario INTEGER, p_desc TEXT, p_voto INTEGER, p_book INTEGER) LANGUAGE plpgsql AS $$
DECLARE v_id INTEGER;
BEGIN
    INSERT INTO Review (description, autore_id, destinatario_id, booking_id) VALUES (p_desc, p_autore, p_destinatario, p_book) RETURNING id INTO v_id;
    INSERT INTO Score (voto, id_recensione) VALUES (p_voto, v_id);
END;
$$;

CREATE OR REPLACE PROCEDURE invia_messaggio(p_chat INTEGER, p_mittente INTEGER, p_testo TEXT) LANGUAGE plpgsql AS $$
BEGIN
    INSERT INTO Message (data_invio, testo, letto, chat_id, mittente_id) VALUES (CURRENT_TIMESTAMP, p_testo, FALSE, p_chat, p_mittente);
    UPDATE Chat SET ultimo_messaggio = CURRENT_TIMESTAMP WHERE id = p_chat;
END;
$$;

CREATE OR REPLACE PROCEDURE controlla_scadenze_prenotazioni() LANGUAGE plpgsql AS $$
DECLARE r RECORD; v_colpevole INTEGER;
BEGIN
    FOR r IN SELECT b.id, b.venue_id, b.band_id, b.iniziato_da FROM Booking b WHERE b.stato_prenotazione = 'pendente' AND b.data_creazione < (CURRENT_TIMESTAMP - INTERVAL '5 days') LOOP
        v_colpevole := NULL;
        IF r.iniziato_da = 'artista' THEN SELECT direttore_id INTO v_colpevole FROM Venue WHERE id = r.venue_id;
        ELSIF r.iniziato_da = 'promoter' THEN SELECT person_id INTO v_colpevole FROM pers_band WHERE band_id = r.band_id LIMIT 1; END IF;
        
        IF v_colpevole IS NOT NULL THEN UPDATE Sanction SET contatoreStrike = contatoreStrike + 1 WHERE person_id = v_colpevole; END IF;
        UPDATE Booking SET stato_prenotazione = 'scaduta', ragione = 'Timeout 5gg' WHERE id = r.id;
    END LOOP;
END;
$$;

COMMIT;