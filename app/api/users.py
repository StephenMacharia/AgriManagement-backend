from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List

from app.db.session import get_db
from app.models.user import User as UserModel
from app.schemas.user import (
    User as UserSchema,
    UserCreate,
    UserUpdate,
    UserInDB,  # still used internally to validate ORM objects if needed
)
from app.auth.security import (
    get_current_active_user,
    is_admin,
    get_password_hash,
)

router = APIRouter()

# --------------------------------------------------------------------
# Get all users (admin only) -> GET /users
# --------------------------------------------------------------------
@router.get("/", response_model=List[UserSchema])
def read_users(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: UserSchema = Depends(is_admin)
):
    users = db.query(UserModel).offset(skip).limit(limit).all()
    return [UserSchema.model_validate(u) for u in users]

# --------------------------------------------------------------------
# Create a new user (admin only) -> POST /users
# --------------------------------------------------------------------
@router.post("/", response_model=UserSchema)
def create_user(
    user: UserCreate,
    db: Session = Depends(get_db),
    current_user: UserSchema = Depends(is_admin)
):
    existing_user = db.query(UserModel).filter(
        (UserModel.username == user.username) | (UserModel.email == user.email)
    ).first()
    if existing_user:
        raise HTTPException(status_code=400, detail="Username or email already registered")

    db_user = UserModel(
        username=user.username,
        email=user.email,
        hashed_password=get_password_hash(user.password),
        full_name=user.full_name,
        phone_number=user.phone_number,
        role=user.role if getattr(user, "role", None) else "farmer",
    )

    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return UserSchema.model_validate(db_user)

# --------------------------------------------------------------------
# Get current user (any logged in user) -> GET /users/me
# --------------------------------------------------------------------
@router.get("/me", response_model=UserSchema)
def read_user_me(current_user: UserModel = Depends(get_current_active_user)):
    return UserSchema.model_validate(current_user)

# --------------------------------------------------------------------
# Get user by ID (self or admin) -> GET /users/{user_id}
# --------------------------------------------------------------------
@router.get("/{user_id}", response_model=UserSchema)
def read_user(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(get_current_active_user)
):
    db_user = db.query(UserModel).filter(UserModel.id == user_id).first()
    if db_user is None:
        raise HTTPException(status_code=404, detail="User not found")

    if current_user.role != "admin" and current_user.id != user_id:
        raise HTTPException(status_code=403, detail="Not enough permissions")

    return UserSchema.model_validate(db_user)

# --------------------------------------------------------------------
# Update user (self or admin) -> PUT /users/{user_id}
# --------------------------------------------------------------------
@router.put("/{user_id}", response_model=UserSchema)
def update_user(
    user_id: int,
    user: UserUpdate,
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(get_current_active_user)
):
    db_user = db.query(UserModel).filter(UserModel.id == user_id).first()
    if db_user is None:
        raise HTTPException(status_code=404, detail="User not found")

    if current_user.role != "admin" and current_user.id != user_id:
        raise HTTPException(status_code=403, detail="Not enough permissions")

    update_data = user.model_dump(exclude_unset=True)

    if "password" in update_data:
        update_data["hashed_password"] = get_password_hash(update_data.pop("password"))

    for field, value in update_data.items():
        setattr(db_user, field, value)

    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return UserSchema.model_validate(db_user)

# --------------------------------------------------------------------
# Delete user (admin only) -> DELETE /users/{user_id}
# --------------------------------------------------------------------
@router.delete("/{user_id}")
def delete_user(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(is_admin)
):
    db_user = db.query(UserModel).filter(UserModel.id == user_id).first()
    if db_user is None:
        raise HTTPException(status_code=404, detail="User not found")

    db.delete(db_user)
    db.commit()
    return {"ok": True}
