from pydantic import BaseModel

class UserLoginRequest(BaseModel):
    username: str
    password: str

class UserRegisterRequest(BaseModel):
    full_name: str
    phone: str
    password: str

