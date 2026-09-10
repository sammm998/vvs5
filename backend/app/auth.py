from __future__ import annotations

import datetime as dt

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
import bcrypt
from sqlalchemy.orm import Session

from .config import settings
from .db import User, get_db

oauth2 = OAuth2PasswordBearer(tokenUrl="/api/auth/login")


def hash_password(p: str) -> str:
    return bcrypt.hashpw(p.encode("utf-8")[:72], bcrypt.gensalt()).decode("ascii")


def verify_password(p: str, h: str) -> bool:
    try:
        return bcrypt.checkpw(p.encode("utf-8")[:72], h.encode("ascii"))
    except ValueError:
        return False


def create_token(user: User) -> str:
    exp = dt.datetime.now(dt.timezone.utc) + dt.timedelta(minutes=settings.access_token_minutes)
    return jwt.encode({"sub": user.id, "email": user.email, "exp": exp}, settings.secret_key, algorithm="HS256")


def current_user(token: str = Depends(oauth2), db: Session = Depends(get_db)) -> User:
    try:
        payload = jwt.decode(token, settings.secret_key, algorithms=["HS256"])
    except jwt.PyJWTError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Ogiltig eller utgången inloggning")
    user = db.get(User, payload.get("sub"))
    if user is None:
        raise HTTPException(status_code=401, detail="Okänd användare")
    return user


def current_admin(user: User = Depends(current_user)) -> User:
    """The one gate the service side sits behind.

    Every admin route depends on this and not on a check written out inside the route, because a check written
    out inside a route is a check somebody forgets to write in the next one. A member reaching an admin route is
    told it is not theirs, not that it does not exist: pretending the page is missing only makes them ask
    support what happened to it.
    """
    if (user.role or "member") != "admin":
        raise HTTPException(status_code=403, detail="Det här är administratörens sidor")
    return user


def current_staff(user: User = Depends(current_user)) -> User:
    """A partner sees their own referrals and their own commission; an admin sees everyone's."""
    if (user.role or "member") not in ("admin", "partner"):
        raise HTTPException(status_code=403, detail="Kräver partner- eller administratörsbehörighet")
    return user
