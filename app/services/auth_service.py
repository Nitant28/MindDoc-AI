from sqlalchemy.orm import Session
from app.database.models import User, Tenant
from app.core.security import hash_password

def create_tenant(db: Session, name: str):
    tenant = Tenant(name=name)
    db.add(tenant)
    db.commit()
    db.refresh(tenant)
    return tenant

def create_user(db: Session, email: str, password: str, tenant_id: int):
    hashed = hash_password(password)
    user = User(email=email, hashed_password=hashed, tenant_id=tenant_id)
    db.add(user)
    db.commit()
    db.refresh(user)
    return user

def update_user(db: Session, user_id: int, email: str = None):
    user = db.query(User).filter(User.id == user_id).first()
    if user:
        if email:
            user.email = email
        db.commit()
        db.refresh(user)
    return user

def get_user_by_email(db: Session, email: str):
    return db.query(User).filter(User.email == email).first()