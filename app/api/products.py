from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, status, Query
from sqlalchemy.orm import Session
from sqlalchemy import or_, and_
from typing import List, Optional
import shutil
import os
from pathlib import Path
from app.db.session import get_db
from app.models.product import Product
from app.schemas.product import Product as ProductSchema, ProductCreate, ProductUpdate
from app.auth.security import get_current_active_user, is_admin, is_salesperson
from app.models.user import User
from app.schemas.pagination import PaginatedResponse

router = APIRouter()

# Configure upload directory
UPLOAD_DIR = Path("uploads/products")
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

class ProductFilter:
    def __init__(
        self,
        category: Optional[str] = None,
        min_price: Optional[float] = None,
        max_price: Optional[float] = None,
        in_stock: Optional[bool] = None,
        search: Optional[str] = None
    ):
        self.category = category
        self.min_price = min_price
        self.max_price = max_price
        self.in_stock = in_stock
        self.search = search

@router.post(
    "/", 
    response_model=ProductSchema, 
    status_code=status.HTTP_201_CREATED,
    summary="Create a new product",
    description="Create a new product. Requires admin privileges."
)
def create_product(
    product: ProductCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(is_admin)
):
    """
    Create a new product in the system.
    
    - **name**: Product name (required)
    - **description**: Product description (optional)
    - **category**: Product category (seed, fertilizer, tool, pesticide, other)
    - **price**: Product price (required)
    - **quantity_in_stock**: Initial stock quantity (required)
    - **unit**: Measurement unit (kg, piece, packet, etc.)
    - **image_url**: Product image URL (optional)
    """
    # Check if product with same name already exists
    existing_product = db.query(Product).filter(Product.name.ilike(product.name)).first()
    if existing_product:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Product with this name already exists"
        )
    
    # Create product instance
    db_product = Product(
        name=product.name,
        description=product.description,
        category=product.category,
        price=product.price,
        quantity_in_stock=product.quantity_in_stock,
        unit=product.unit,
        image_url=product.image_url,
        created_by=current_user.id
    )
    db.add(db_product)
    db.commit()
    db.refresh(db_product)
    return db_product

@router.get(
    "/", 
    response_model=PaginatedResponse[ProductSchema],
    summary="Get all products with advanced filtering",
    description="Retrieve a paginated list of products with advanced filtering options."
)
def read_products(
    page: int = Query(1, ge=1, description="Page number starting from 1"),
    per_page: int = Query(20, ge=1, le=100, description="Items per page (1-100)"),
    category: Optional[str] = Query(None, description="Filter by category"),
    min_price: Optional[float] = Query(None, ge=0, description="Minimum price filter"),
    max_price: Optional[float] = Query(None, ge=0, description="Maximum price filter"),
    in_stock: Optional[bool] = Query(None, description="Filter products in stock only"),
    search: Optional[str] = Query(None, description="Search in product name and description"),
    sort_by: str = Query("name", description="Sort by field: name, price, created_at, updated_at"),
    sort_order: str = Query("asc", description="Sort order: asc or desc"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Retrieve products with advanced filtering, sorting, and pagination.
    
    - **page**: Page number (default: 1)
    - **per_page**: Items per page (default: 20, max: 100)
    - **category**: Filter by product category
    - **min_price**: Minimum price filter
    - **max_price**: Maximum price filter
    - **in_stock**: Only show products with stock available
    - **search**: Search term in name and description
    - **sort_by**: Field to sort by (name, price, created_at, updated_at)
    - **sort_order**: Sort order (asc or desc)
    """
    # Build query
    query = db.query(Product)
    
    # Apply filters
    if category:
        query = query.filter(Product.category == category)
    
    if min_price is not None:
        query = query.filter(Product.price >= min_price)
    
    if max_price is not None:
        query = query.filter(Product.price <= max_price)
    
    if in_stock:
        query = query.filter(Product.quantity_in_stock > 0)
    
    if search:
        search_filter = or_(
            Product.name.ilike(f"%{search}%"),
            Product.description.ilike(f"%{search}%")
        )
        query = query.filter(search_filter)
    
    # Validate sort parameters
    valid_sort_fields = ["name", "price", "created_at", "updated_at"]
    if sort_by not in valid_sort_fields:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid sort field. Must be one of: {', '.join(valid_sort_fields)}"
        )
    
    if sort_order not in ["asc", "desc"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Sort order must be 'asc' or 'desc'"
        )
    
    # Apply sorting
    sort_column = getattr(Product, sort_by)
    if sort_order == "desc":
        sort_column = sort_column.desc()
    query = query.order_by(sort_column)
    
    # Calculate pagination
    total_count = query.count()
    total_pages = (total_count + per_page - 1) // per_page
    
    # Apply pagination
    products = query.offset((page - 1) * per_page).limit(per_page).all()
    
    # Build pagination response
    return {
        "items": products,
        "total": total_count,
        "page": page,
        "per_page": per_page,
        "total_pages": total_pages,
        "has_next": page < total_pages,
        "has_prev": page > 1
    }

@router.get(
    "/{product_id}", 
    response_model=ProductSchema,
    summary="Get product by ID",
    description="Retrieve a specific product by its ID."
)
def read_product(
    product_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Get a specific product by ID.
    
    - **product_id**: ID of the product to retrieve
    """
    db_product = db.query(Product).filter(Product.id == product_id).first()
    if db_product is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, 
            detail="Product not found"
        )
    return db_product

@router.put(
    "/{product_id}", 
    response_model=ProductSchema,
    summary="Update a product",
    description="Update an existing product. Requires admin privileges."
)
def update_product(
    product_id: int,
    product: ProductUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(is_admin)
):
    """
    Update an existing product.
    
    - **product_id**: ID of the product to update
    - **name**: Product name (optional)
    - **description**: Product description (optional)
    - **category**: Product category (optional)
    - **price**: Product price (optional)
    - **quantity_in_stock**: Stock quantity (optional)
    - **unit**: Measurement unit (optional)
    - **image_url**: Product image URL (optional)
    """
    db_product = db.query(Product).filter(Product.id == product_id).first()
    if db_product is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, 
            detail="Product not found"
        )
    
    # Check if name change would cause conflict
    if product.name and product.name != db_product.name:
        existing_product = db.query(Product).filter(
            Product.name.ilike(product.name),
            Product.id != product_id
        ).first()
        if existing_product:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Another product with this name already exists"
            )
    
    update_data = product.dict(exclude_unset=True)
    for field in update_data:
        setattr(db_product, field, update_data[field])
    
    db.add(db_product)
    db.commit()
    db.refresh(db_product)
    return db_product

@router.delete(
    "/{product_id}",
    status_code=status.HTTP_200_OK,
    summary="Delete a product",
    description="Delete a product. Requires admin privileges."
)
def delete_product(
    product_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(is_admin)
):
    """
    Delete a product from the system.
    
    - **product_id**: ID of the product to delete
    """
    db_product = db.query(Product).filter(Product.id == product_id).first()
    if db_product is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, 
            detail="Product not found"
        )
    
    # Optional: Delete associated image file if exists
    if db_product.image_url and db_product.image_url.startswith('/uploads/'):
        try:
            image_path = Path(db_product.image_url[1:])  # Remove leading slash
            if image_path.exists():
                image_path.unlink()
        except Exception as e:
            # Log the error but don't fail the delete operation
            print(f"Error deleting image file: {e}")
    
    db.delete(db_product)
    db.commit()
    return {"ok": True, "message": "Product deleted successfully"}

@router.post(
    "/{product_id}/upload-image",
    summary="Upload product image",
    description="Upload an image for a product. Requires admin privileges."
)
def upload_product_image(
    product_id: int,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(is_admin)
):
    """
    Upload an image for a specific product.
    
    - **product_id**: ID of the product to upload image for
    - **file**: Image file to upload (JPG, PNG, etc.)
    """
    db_product = db.query(Product).filter(Product.id == product_id).first()
    if db_product is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, 
            detail="Product not found"
        )
    
    # Validate file type
    allowed_extensions = {'.jpg', '.jpeg', '.png', '.gif', '.webp'}
    file_extension = os.path.splitext(file.filename)[1].lower()
    if file_extension not in allowed_extensions:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid file type. Allowed types: JPG, JPEG, PNG, GIF, WEBP"
        )
    
    try:
        # Generate a safe filename
        safe_filename = f"product_{product_id}{file_extension}"
        file_location = UPLOAD_DIR / safe_filename
        
        # Save the file
        with open(file_location, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        
        # Update product with relative image URL
        db_product.image_url = f"/uploads/products/{safe_filename}"
        db.add(db_product)
        db.commit()
        db.refresh(db_product)
        
        return {
            "filename": safe_filename, 
            "location": str(file_location),
            "message": "Image uploaded successfully",
            "image_url": db_product.image_url
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, 
            detail=f"Error uploading image: {str(e)}"
        )

@router.get(
    "/category/{category_name}",
    response_model=List[ProductSchema],
    summary="Get products by category",
    description="Retrieve all products in a specific category."
)
def get_products_by_category(
    category_name: str,
    page: int = Query(1, ge=1, description="Page number starting from 1"),
    per_page: int = Query(20, ge=1, le=100, description="Items per page (1-100)"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Get products filtered by category.
    
    - **category_name**: Category to filter by (seed, fertilizer, tool, pesticide, other)
    - **page**: Page number (default: 1)
    - **per_page**: Items per page (default: 20, max: 100)
    """
    valid_categories = ['seed', 'fertilizer', 'tool', 'pesticide', 'other']
    if category_name not in valid_categories:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid category. Must be one of: {', '.join(valid_categories)}"
        )
    
    query = db.query(Product).filter(Product.category == category_name)
    total_count = query.count()
    
    products = query.offset((page - 1) * per_page).limit(per_page).all()
    
    return products

@router.get(
    "/search/{search_term}",
    response_model=List[ProductSchema],
    summary="Search products",
    description="Search products by name or description."
)
def search_products(
    search_term: str,
    page: int = Query(1, ge=1, description="Page number starting from 1"),
    per_page: int = Query(20, ge=1, le=100, description="Items per page (1-100)"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Search products by name or description.
    
    - **search_term**: Term to search for
    - **page**: Page number (default: 1)
    - **per_page**: Items per page (default: 20, max: 100)
    """
    query = db.query(Product).filter(
        or_(
            Product.name.ilike(f"%{search_term}%"),
            Product.description.ilike(f"%{search_term}%")
        )
    )
    
    products = query.offset((page - 1) * per_page).limit(per_page).all()
    return products

# Add this schema for pagination response
from pydantic import BaseModel
from typing import Generic, TypeVar, List

T = TypeVar('T')

class PaginatedResponse(BaseModel, Generic[T]):
    items: List[T]
    total: int
    page: int
    per_page: int
    total_pages: int
    has_next: bool
    has_prev: bool

    class Config:
        from_attributes = True