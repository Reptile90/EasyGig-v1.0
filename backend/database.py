import os
from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker,declarative_base

load_dotenv()

db_password = os.getenv("DB_PASSWORD")

SQLALCHEMY_DATABSE_URL = f"postgresql://postgres:{db_password}@localhost/easygig"

engine = create_engine(SQLALCHEMY_DATABSE_URL)

SessionLocal = sessionmaker(autocommit=False, autoflush=False,bind=engine)

Base = declarative_base()