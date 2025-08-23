from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlalchemy.orm import Session
from typing import List
import shutil
import os
from pathlib import Path
from app.db.session import get_db
from app.models.produce import Produce
from app.schemas.user import User, UserCreate, UserUpdate, UserInDB
from app.schemas.produce import Produce, ProduceCreate, ProduceUpdate
from app.auth.security import get_current_active_user, is_farmer

router = APIRouter()

# Configure upload directory
UPLOAD_DIR = Path("uploads/produce")
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

@router.post("/", response_model=Produce)
def create_produce(
    produce: ProduceCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(is_farmer)
):
    db_produce = Produce(**produce.dict(), farmer_id=current_user.id)
    db.add(db_produce)
    db.commit()
    db.refresh(db_produce)
    return db_produce

@router.get("/", response_model=List[Produce])
def read_produce(
    skip: int = 0,
    limit: int = 100,
    category: str = None,
    farmer_id: int = None,
    available: bool = True,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    query = db.query(Produce).filter(Produce.is_available == available)
    
    if category:
        query = query.filter(Produce.category == category)
    if farmer_id:
        # Only admin can filter by other farmers
        if current_user.role != "admin" and current_user.id != farmer_id:
            raise HTTPException(status_code=403, detail="Not enough permissions")
        query = query.filter(Produce.farmer_id == farmer_id)
    elif current_user.role == "farmer":
        # Farmers can only see their own produce by default
        query = query.filter(Produce.farmer_id == current_user.id)
    
    produce = query.offset(skip).limit(limit).all()
    return produce

@router.get("/{produce_id}", response_model=Produce)
def read_produce_item(
    produce_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    db_produce = db.query(Produce).filter(Produce.id == produce_id).first()
    if db_produce is None:
        raise HTTPException(status_code=404, detail="Produce not found")
    
    # Only admin or the owner farmer can see the produce
    if current_user.role != "admin" and current_user.id != db_produce.farmer_id:
        raise HTTPException(status_code=403, detail="Not enough permissions")
    
    return db_produce

@router.put("/{produce_id}", response_model=Produce)
def update_produce(
    produce_id: int,
    produce: ProduceUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    db_produce = db.query(Produce).filter(Produce.id == produce_id).first()
    if db_produce is None:
        raise HTTPException(status_code=404, detail="Produce not found")
    
    # Only admin or the owner farmer can update
    if current_user.role != "admin" and current_user.id != db_produce.farmer_id:
        raise HTTPException(status_code=403, detail="Not enough permissions")
    
    update_data = produce.dict(exclude_unset=True)
    for field in update_data:
        setattr(db_produce, field, update_data[field])
    
    db.add(db_produce)
    db.commit()
    db.refresh(db_produce)
    return db_produce

@router.delete("/{produce_id}")
def delete_produce(
    produce_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    db_produce = db.query(Produce).filter(Produce.id == produce_id).first()
    if db_produce is None:
        raise HTTPException(status_code=404, detail="Produce not found")
    
    # Only admin or the owner farmer can delete
    if current_user.role != "admin" and current_user.id != db_produce.farmer_id:
        raise HTTPException(status_code=403, detail="Not enough permissions")
    
    db.delete(db_produce)
    db.commit()
    return {"ok": True}

@router.post("/{produce_id}/upload-image")
def upload_produce_image(
    produce_id: int,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    db_produce = db.query(Produce).filter(Produce.id == produce_id).first()
    if db_produce is None:
        raise HTTPException(status_code=404, detail="Produce not found")
    
    # Only admin or the owner farmer can upload
    if current_user.role != "admin" and current_user.id != db_produce.farmer_id:
        raise HTTPException(status_code=403, detail="Not enough permissions")
    
    try:
        # Save the file
        file_location = UPLOAD_DIR / f"produce_{produce_id}_{file.filename}"
        with open(file_location, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        
        # Update produce with image URL
        db_produce.image_url = str(file_location)
        db.add(db_produce)
        db.commit()
        
        return {"filename": file.filename, "location": str(file_location)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))