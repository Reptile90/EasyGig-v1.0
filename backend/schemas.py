from pydantic import BaseModel,EmailStr

class UserCreate(BaseModel):
    nome:str
    cognome:str
    email:EmailStr
    password:str
    privacy:bool