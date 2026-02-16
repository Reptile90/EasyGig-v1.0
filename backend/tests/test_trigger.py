from app.core.database import SessionLocal
from app.models.models import Person
from sqlalchemy.exc import InternalError, IntegrityError

db = SessionLocal()

print("--- 💥 STRESS TEST: CANCELLAZIONE VIETATA ---")

# Prendiamo la prima persona che troviamo (Adrian)
vittima = db.query(Person).first()

if vittima:
    print(f"Tentativo di cancellare: {vittima.nome} {vittima.cognome}...")
    print(f"(È l'unico membro dell'organizzazione {vittima.organization.nome})")
    
    try:
        db.delete(vittima)
        db.commit()
        print("❌ ERRORE: Il database ha permesso la cancellazione! Il trigger non ha funzionato.")
    except (InternalError, IntegrityError) as e:
        db.rollback() # Annulla tutto
        print("\n✅ SUCCESSO! Il database ha bloccato l'operazione.")
        print("Messaggio dal DB:")
        # Cerchiamo di stampare solo la parte rilevante dell'errore
        print(e.orig) 
else:
    print("Nessuna persona trovata da cancellare.")
