from sqlalchemy import Column,Integer,String,ForeignKey,Boolean,Text,DECIMAL,Enum,CheckConstraint,ForeignKeyConstraint,DATE,Time,DateTime, UniqueConstraint,func
from sqlalchemy.orm import relationship
from app.core.database import Base
import enum

#ENUM
class PersonType(enum.Enum):
    artista = 'artista'
    promoter = 'promoter'
    direttoreArtistico = 'direttoreArtistico'
    
class BandCategory(enum.Enum):
    inedita = 'inedita'
    tributeBand = 'tributeBand'
    coverBand = 'coverBand'
    
class OrganizationType(enum.Enum):
    agenzia = 'agenzia'
    crew = 'crew'
    collettivo = 'collettivo'
    individuale = 'individuale'
    
class VenueType(enum.Enum):
    inPiedi = 'inPiedi'
    platea = 'platea'
    tavoli = 'tavoli'
    misto = 'misto'
    
class BookingState(enum.Enum):
    pendente = 'pendente'
    accettata = 'accettata'
    rifiutata = 'rifiutata'
    scaduta = 'scaduta'
    annullata = 'annullata'

class SlotType(enum.Enum):
    disponibile = 'disponibile'
    inTrattativa = 'inTrattativa'
    occupato = 'occupato'
    
class StateAccountType(enum.Enum):
    attivo = 'attivo'
    warning = 'warning'
    congelato = 'congelato'
    
class StateInvitation(enum.Enum):
    pending='pending'
    accepted ='accepted'
    expired = 'expired'
    
#TABELLA NATION
class Nation(Base):
    __tablename__ = "nation"
    nome = Column(String, primary_key=True)
    
#TABELLA REGION
class Region(Base):
    __tablename__ = "region"
    nome = Column(String,primary_key=True)
    nazione = Column(String ,ForeignKey('nation.nome'), primary_key=True, nullable=False)
    
#TABELLA CITY
class City(Base):
    __tablename__ = "city"
    
    id = Column(Integer, primary_key=True, index=True)
    nome = Column(String, nullable=False)
    
    regione = Column(String, nullable=False)
    nazione = Column(String, nullable=False)
    
    __table_args__ = (
        
        ForeignKeyConstraint(
            ['nazione', 'regione'],
            ['region.nazione', 'region.nome']
        ),
    )
    
    
    residents = relationship("Person", back_populates="city")
    region_obj = relationship("Region")
    
#TABELLA ADDRESS
class Address(Base):
    __tablename__ = 'address'
    id = Column(Integer, primary_key=True)
    via = Column(String, nullable=False)
    civico = Column(String, nullable=False)
    cap = Column(String, nullable=False)
    citta_id = Column(Integer,ForeignKey('city.id'), nullable=False)
    
#TABELLA GENRE
class Genre(Base):
    __tablename__ = 'genre'
    id = Column(Integer, primary_key=True)
    nome = Column(String, nullable=False)
    #Relazioni
    artists = relationship("Person", back_populates="genre")
    bands = relationship("Band", back_populates='genre')
#TABELLA BOOKING ORGANIZATION
class BookingOrganization(Base):
    __tablename__= 'booking_organization'
    id = Column(Integer, primary_key=True)
    nome = Column(String, nullable=False)
    storico_eventi = Column(Text, nullable=True)
    tipo_booking = Column(Enum(OrganizationType), nullable=False)
    #Relazioni
    members = relationship("Person", back_populates="organization")
    
    
#TABELLA PERSON
class Person(Base):
    __tablename__ = "person"
    
    id= Column(Integer, primary_key=True, index = True)
    nome = Column(String, nullable=False)
    cognome = Column(String, nullable=False)
    telefono = Column(String, unique=True, nullable=False)
    email = Column(String, unique=True, nullable=False)
    tipo_utente = Column(Enum(PersonType))
    password_hash = Column(String, nullable=True)
    link_streaming = Column(String, nullable=True)
    file_path = Column(String, nullable=True)
    reputazione = Column(DECIMAL(3,2), default=0.00)
    privacy_accettata = Column(Boolean, nullable=False)
    
    #Relazioni
    city_id = Column(Integer, ForeignKey("city.id"), nullable=False)
    genere_id = Column(Integer, ForeignKey('genre.id'), nullable=True)
    organization_id = Column(Integer, ForeignKey('booking_organization.id'), nullable=True)
    organization = relationship("BookingOrganization", back_populates='members')
    city = relationship("City", back_populates="residents")
    managed_venues = relationship("Venue", back_populates="direttore")
    list_reviews = relationship("Review", back_populates="autore", foreign_keys="[Review.autore_id]")
    reviews = relationship("Review", back_populates="destinatario", foreign_keys="[Review.destinatario_id]")
    sanzioni = relationship('Sanction', back_populates='persona_sanzionata')
    accounts = relationship('StatoAccount', back_populates="account_persona")
    photolist = relationship('Photo', back_populates="person_foto")
    membro_band = relationship('Invitation', back_populates='persona')
    
    __table_args__ = (
        CheckConstraint(
            "(tipo_utente != 'artista') OR (link_streaming IS NOT NULL) OR (file_path IS NOT NULL)",
            name='check_artista_content'
        ),)
#TABELLA BAND
class Band(Base):
    __tablename__ = 'band'
    id = Column(Integer, primary_key=True)
    nome = Column(String, nullable=False)
    cachet = Column(Integer, nullable=False)
    trattabile = Column(Boolean, nullable=False, default=False)
    categoria = Column(Enum(BandCategory), nullable=False)
    
    #Relazioni
    genere_id = Column(Integer, ForeignKey('genre.id'), nullable=False)
    genre = relationship("Genre", back_populates="bands")
    bookings = relationship("Booking", back_populates='bands_bookings')
    band_list = relationship("Invitation", back_populates='membri')
    
#TABELLA ASSOCIAZIONE PERSONA-BAND
class pers_band(Base):
    __tablename__ = 'pers_band'
    person_id = Column(Integer, ForeignKey('person.id'), primary_key=True, nullable=False)
    band_id = Column(Integer, ForeignKey('band.id'), primary_key=True, nullable=False)

class Invitation(Base):
    __tablename__ = 'invitation'
    id = Column(Integer, primary_key=True)
    email = Column(String, nullable=False)
    token = Column(String, nullable=False, unique=True)
    stato = Column(Enum(StateInvitation), nullable=False, default='pending')
    data_invio = Column(DateTime, nullable=False, default=func.now())
    
    # Relazioni
    band_id = Column(Integer, ForeignKey('band.id'), nullable=False)
    person_id = Column(Integer, ForeignKey('person.id'), nullable=True)
    sender_id = Column(Integer, ForeignKey('person.id'), nullable=False)
    membri = relationship('Band', back_populates="band_list")
    persona = relationship('Person', foreign_keys=[person_id], back_populates='membro_band')
    mittente = relationship('Person', foreign_keys=[sender_id])
#TABELLA VENUE
class Venue(Base):
    __tablename__ ='venue'
    id = Column(Integer, primary_key=True)
    nome = Column(String, nullable=False)
    email = Column(String, unique=True, nullable=False)
    telefono = Column(String, unique=True, nullable=False)
    tipo_sala = Column(Enum(VenueType), nullable=False)
    capienza = Column(Integer, nullable=False)
    strumentazione = Column(Text, nullable=False)
    
    
    #Relazioni
    city_id = Column(Integer, ForeignKey('city.id'), nullable=False)
    direttore_id = Column(Integer, ForeignKey('person.id'), nullable=False)
    venue_city = relationship("City")
    direttore = relationship("Person", back_populates="managed_venues")
    photolist = relationship('Photo', back_populates='venue_foto')
    calendarlist = relationship('Calendar', back_populates='venue_calendar')
    
    
#TABELLA FOTO
class Photo(Base):
    __tablename__='photo'
    id = Column(Integer, primary_key=True)
    nome = Column(String, nullable=False)
    source = Column(String, nullable=False)
    #Relazioni
    venue_id = Column(Integer, ForeignKey('venue.id'),nullable=True)
    person_id = Column(Integer, ForeignKey('person.id'), nullable=True)
    venue_foto = relationship("Venue", back_populates='photolist')
    person_foto = relationship("Person", back_populates='photolist')
    __table_args__ = (
        CheckConstraint(
            "(venue_id IS NOT NULL AND person_id IS NULL) OR (venue_id IS NULL AND person_id IS NOT NULL)",
            name="check_photo_owner"
        ),
    )
    
    
#TABELLA CALENDAR

class Calendar(Base):
    __tablename__='calendar'
    id = Column(Integer, primary_key=True)
    slot_disponibili = Column(Integer, nullable=False)
    data = Column(DATE, nullable=False)
    data_inizio = Column(Time, nullable=False)
    data_fine = Column(Time, nullable=False)
    
    #Relazioni
    venue_id = Column(Integer, ForeignKey('venue.id'))
    venue_calendar = relationship("Venue", back_populates='calendarlist')
    slots = relationship('Slot', back_populates= 'calendar_event')

#TABELLA SLOT
class Slot(Base):
    __tablename__ = 'slot'
    
    id = Column(Integer, primary_key=True)
    orario_inizio = Column(Time, nullable=False)
    orario_fine = Column(Time, nullable=False)
    stato = Column(Enum(SlotType), nullable=False, default='disponibile')
    
    #Relazioni
    calendar_id = Column(Integer, ForeignKey('calendar.id'), nullable=False)
    calendar_event = relationship("Calendar", back_populates="slots")
    
#TABELLA BOOKING
class Booking(Base):
    __tablename__ = 'booking'
    id = Column(Integer, primary_key=True)
    data_creazione = Column(DateTime, nullable=False, default=func.now())
    message = Column(Text, nullable=False)
    scadenza = Column(DateTime, nullable=False)
    stato_prenotazione = Column(Enum(BookingState), nullable=False)
    ragione = Column(Text, nullable=True)
    iniziato_da = Column(Enum(PersonType), nullable=False, default='artista')
    
    #Relazioni
    band_id = Column(Integer, ForeignKey('band.id'), nullable=False)
    slot_id = Column(Integer, ForeignKey('slot.id'), nullable=False)
    bands_bookings = relationship("Band", back_populates='bookings')
    slot_item = relationship("Slot")
    chats = relationship('Chat', back_populates='chat_prenotazioni')
    booking_reviews= relationship('Review', back_populates='prenotazione')
    
    __table_args__ = (
        CheckConstraint(
            "(stato_prenotazione != 'annullata') OR (ragione IS NOT NULL)",
            name='ragione_obbligatoria_annullata'
        ),
    )
#TABELLA BOOK_CAL
class book_cal(Base):
    __tablename__ = 'book_cal'
    booking_id = Column(Integer, ForeignKey('booking.id'), primary_key=True)
    calendar_id = Column(Integer, ForeignKey('calendar.id'), primary_key=True)
    
#TABELLA CHAT
class Chat(Base):
    __tablename__ ='chat'
    id = Column(Integer, primary_key=True)
    data_apertura = Column(DateTime, nullable=False, default=func.now())
    ultimo_messaggio = Column(DateTime, nullable=True)
    
    #Relazioni
    booking_id = Column(Integer, ForeignKey('booking.id'), nullable=False)
    chat_prenotazioni = relationship('Booking', back_populates="chats")
    messages = relationship('Message', back_populates='chatlist')
    

#TABELLA MESSAGE
class Message(Base):
    __tablename__ = 'message'
    id = Column(Integer, primary_key=True)
    data_invio = Column(DateTime, nullable=False, default=func.now())
    testo = Column(Text, nullable=False)
    letto = Column(Boolean, nullable=True, default=False)
    
    #Relazioni
    chat_id = Column(Integer, ForeignKey('chat.id'), nullable=False)
    mittente_id = Column(Integer, ForeignKey('person.id'), nullable= False)
    chatlist = relationship('Chat', back_populates="messages")
    
#TABELLA REVIEW
class Review(Base):
    __tablename__ = 'review'
    id = Column(Integer, primary_key=True)
    data_creazione = Column(DateTime, nullable=False, default=func.now())
    description = Column(Text, nullable=False)
    
    #Relazioni
    autore_id = Column(Integer, ForeignKey('person.id'), nullable=False)
    destinatario_id = Column(Integer, ForeignKey('person.id'), nullable=False)
    booking_id = Column(Integer, ForeignKey('booking.id'), nullable=False)
    autore = relationship("Person", back_populates="list_reviews", foreign_keys=[autore_id])
    destinatario = relationship("Person", back_populates="reviews", foreign_keys=[destinatario_id])
    prenotazione = relationship("Booking", back_populates="booking_reviews")
    votazioni = relationship("Score", back_populates='recensione', cascade="all, delete-orphan")
    
    __table_args__ = (
        CheckConstraint('autore_id != destinatario_id', name='check_no_auto_recensione'),
        UniqueConstraint('booking_id', 'autore_id', name='una_recensione_per_booking')
    )
#TABELLA SCORE
class Score(Base):
    __tablename__ = 'score'
    id = Column(Integer, primary_key=True)
    data_creazione = Column(DateTime, nullable=False, default=func.now())
    voto = Column(Integer, nullable=False)
    
    #Relazioni
    review_id = Column(Integer, ForeignKey('review.id'), nullable=False)
    recensione = relationship('Review', back_populates='votazioni')
    __table_args__ = (
        CheckConstraint('voto >= 0 AND voto <= 5', name='check_voto_range'),)
    
#TABELLA SANCTION
class Sanction(Base):
    __tablename__ = 'sanction'
    id = Column(Integer, primary_key=True)
    contatorestrike = Column(Integer, nullable=False)
    soglia_warning = Column(Integer, nullable=False)
    soglia_ban = Column(Integer, nullable=False)
    
    #Relazioni
    person_id = Column(Integer, ForeignKey('person.id'), nullable=False)
    data_ultimo_ban = Column(DateTime, nullable=True)
    persona_sanzionata = relationship('Person', back_populates="sanzioni")
    
#TABELLA STATO ACCOUNT
class StatoAccount(Base):
    __tablename__ = 'stato_account'
    id = Column(Integer, primary_key=True)
    stato = Column(Enum(StateAccountType), nullable=False)
    istante = Column(DateTime, nullable=False, default=func.now())
    
    #Relazioni
    person_id = Column(Integer, ForeignKey('person.id'), nullable = False)
    account_persona = relationship("Person", back_populates="accounts")
