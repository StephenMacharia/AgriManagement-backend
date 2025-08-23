from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.db.init import init_db
from app.api import (
    users, products, produce, transactions, credits, commissions, reports
)
from app.auth.jwt import router as auth_router

app = FastAPI(
    title="agribusiness",
    description="Backend API for AgriLink360 agricultural platform",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# CORS configuration
origins = [
    "http://localhost",
    "http://localhost:3000",
    "https://your-frontend-domain.com"
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize database
@app.on_event("startup")
async def startup_event():
    init_db()

# Include routers
app.include_router(auth_router, prefix="/auth", tags=["auth"])
app.include_router(users.router, prefix="/users", tags=["users"])
app.include_router(products.router, prefix="/products", tags=["products"])
app.include_router(produce.router, prefix="/produce", tags=["produce"])
app.include_router(transactions.router, prefix="/transactions", tags=["transactions"])
app.include_router(credits.router, prefix="/credits", tags=["credits"])
app.include_router(commissions.router, prefix="/commissions", tags=["commissions"])
app.include_router(reports.router, prefix="/reports", tags=["reports"])

@app.get("/")
def read_root():
    return {"message": "Welcome to AgriLink360 API"}