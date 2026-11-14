from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.core.security import RateLimiter, verify_token
from app.database.models import User, get_db
from app.database.tenancy import set_tenant

security = HTTPBearer()


def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security), db: Session = Depends(get_db)):
    payload = verify_token(credentials.credentials)
    if not payload or "sub" not in payload:
        raise HTTPException(status_code=401, detail="Invalid token")
    user = db.query(User).filter(User.id == int(payload["sub"])).first()
    if not user or user.is_active is False:
        raise HTTPException(status_code=401, detail="User not found or deactivated")
    # Bind this request's session to the user's tenant: row-level security on PostgreSQL, and tenant_id filled on
    # every new row (app/database/tenancy.py). Endpoints share this session through FastAPI's per-request cache.
    set_tenant(db, user.tenant_id)
    return user


def enforce_rate(limiter: RateLimiter, user) -> None:
    if not limiter.allow(f"user:{user.id}"):
        raise HTTPException(status_code=429, detail="Rate limit reached. Please wait a minute and try again.")
