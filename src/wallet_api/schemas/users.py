import re
import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, field_validator

from wallet_api.schemas.wallets import WalletResponse

pattern = r"^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)(?=.*[-&_@!%~])[a-zA-Z\d&_@!%~]{8,}$"


class BaseUser(BaseModel):
    email: EmailStr


class UserCreate(BaseUser):
    password_hash: str

    @field_validator("password_hash", mode="after")
    @classmethod
    def valid_password(cls, psw):
        if not re.match(pattern, psw):
            raise ValueError(
                "Пароль должен быть не короче 8 символов,"
                "содержать буквы разного регистра, и"
                "хотябы один из символов - -&_@!%~ "
            )

        return psw


class UserResponse(BaseUser):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    created_at: datetime
    wallets: list[WalletResponse] | None = None


class TokenResponse(BaseModel):
    expires_in: datetime
