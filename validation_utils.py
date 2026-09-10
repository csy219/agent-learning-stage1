from pydantic import BaseModel



class Contact(BaseModel):
    name:str
    phone:str
    date:str

def validate_contact(raw_json:str)->Contact:
    """把json字符串校验成Contact对象,不合格会抛ValidationError"""
    return Contact.model_validate_json(raw_json)