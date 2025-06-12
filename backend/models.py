# backend/models.py
from pydantic import BaseModel

class UserLogin(BaseModel):
    rut: str
    password: str
