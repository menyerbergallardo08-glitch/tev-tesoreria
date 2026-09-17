from pydantic import BaseModel

class CleanSlateRequest(BaseModel):
    master_key: str
    confirmation_phrase: str # Debe ser 'CONFIRMAR-PURGA-TEV'
