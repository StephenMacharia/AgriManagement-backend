from datetime import timedelta
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.user import User
from app.schemas.user import Token, UserWithToken, UserCreate, UserInDB
from app.auth.security import (
    get_password_hash,
    verify_password,
    create_access_token,
    ACCESS_TOKEN_EXPIRE_MINUTES,
)

router = APIRouter(tags=["auth"])

# LOGIN: returns user + token (frontend-friendly)
@router.post("/login", response_model=UserWithToken)
async def login_with_user(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db)
):
    user = db.query(User).filter(User.username == form_data.username).first()
    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(data={"sub": user.username}, expires_delta=access_token_expires)

    return UserWithToken(
        user=UserInDB.model_validate(user),  # ensure Pydantic v2 validation
        access_token=access_token,
        token_type="bearer"
    )

# TOKEN-ONLY: OAuth2 compatibility (for Swagger/OAuth2PasswordBearer)
@router.post("/token", response_model=Token)
async def login_token_only(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db)
):
    user = db.query(User).filter(User.username == form_data.username).first()
    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(data={"sub": user.username}, expires_delta=access_token_expires)

    return {"access_token": access_token, "token_type": "bearer"}

# REGISTER: create user + return user + token
# REGISTER: create user + return user + token
@router.post("/register", response_model=UserWithToken)
async def register_user(
    user_data: UserCreate,
    db: Session = Depends(get_db)
):
    existing_user = db.query(User).filter(
        (User.username == user_data.username) | (User.email == user_data.email)
    ).first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username or email already registered"
        )

    hashed_password = get_password_hash(user_data.password)
    
    # ✅ FIXED: Use role from user input if provided, otherwise default to "farmer"
    db_user = User(
        username=user_data.username,
        email=user_data.email,
        hashed_password=hashed_password,
        full_name=user_data.full_name,
        phone_number=user_data.phone_number,
        role=user_data.role if user_data.role else "farmer",  # ✅ Use input role or default
    )

    db.add(db_user)
    db.commit()
    db.refresh(db_user)

    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(data={"sub": db_user.username}, expires_delta=access_token_expires)

    return UserWithToken(
        user=UserInDB.model_validate(db_user),
        access_token=access_token,
        token_type="bearer"
    )