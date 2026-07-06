from pydantic import BaseModel, ConfigDict
from typing import Optional

class UserBase(BaseModel):
    username: str

class UserCreate(UserBase):
    password: str
    household_name: Optional[str] = "My Household"

class UserLogin(UserBase):
    password: str

class UserResponse(UserBase):
    id: int
    household_id: int
    
    model_config = ConfigDict(from_attributes=True)

class Token(BaseModel):
    access_token: str
    token_type: str
    username: str
    household_id: int

class HouseholdResponse(BaseModel):
    id: int
    name: str

    model_config = ConfigDict(from_attributes=True)
