from fastapi import Depends, HTTPException, Request
from passlib.context import CryptContext
from sqlalchemy.orm import Session

from database import get_db
from models.user import User

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


async def get_current_user(request: Request, db: Session = Depends(get_db)) -> User:
    user_id = request.session.get("user_id")
    if not user_id:
        raise HTTPException(status_code=303, headers={"Location": "/auth/login"})
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        request.session.clear()
        raise HTTPException(status_code=303, headers={"Location": "/auth/login"})
    return user
