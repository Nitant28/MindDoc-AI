from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.core.security import RateLimiter, verify_token
from app.database.models import User, get_db

security = HTTPBearer()


def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security), db: Session = Depends(get_db)):
    payload = verify_token(credentials.credentials)
    if not payload or "sub" not in payload:
        raise HTTPException(status_code=401, detail="Invalid token")
    user = db.query(User).filter(User.id == int(payload["sub"])).first()
    if not user:
        raise HTTPException(status_code=401, detail="User not found")
    return user


def enforce_rate(limiter: RateLimiter, user) -> None:
    if not limiter.allow(f"user:{user.id}"):
        raise HTTPException(status_code=429, detail="Rate limit reached. Please wait a minute and try again.")
