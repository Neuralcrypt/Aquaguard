from pydantic import BaseModel, Field


class LoginRequest(BaseModel):
    username: str = Field(min_length=1, max_length=100)
    password: str = Field(min_length=1, max_length=128)


class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    role: str
    username: str
    hostel_id: int | None = None
    hostel_name: str | None = None


class HostelCreate(BaseModel):
    hostel_name: str = Field(min_length=2, max_length=150)
    username: str = Field(min_length=3, max_length=50, pattern=r"^[A-Za-z0-9_-]+$")
    password: str = Field(min_length=6, max_length=128)


class HostelUpdate(BaseModel):
    hostel_name: str = Field(min_length=2, max_length=150)
    is_active: bool


class PasswordReset(BaseModel):
    new_password: str = Field(min_length=6, max_length=128)


class HostelOut(BaseModel):
    id: int
    hostel_name: str
    username: str
    is_active: bool

    class Config:
        from_attributes = True


class UsernameUpdate(BaseModel):
        username: str = Field(
            min_length=3,
            max_length=50,
            pattern=r"^[A-Za-z0-9_-]+$"
    )