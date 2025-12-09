from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.sessions import SessionMiddleware
from app.core.config import get_settings
from app.database import engine, Base

# Import all models to register them with SQLAlchemy
from app.models import User, Wallet, Transaction

settings = get_settings()

# Create FastAPI app instance
app = FastAPI(
    title=settings.APP_NAME,
    debug=settings.DEBUG,
    version="1.0.0"
)

# Session middleware - required for OAuth2 flows
app.add_middleware(SessionMiddleware, secret_key=settings.SECRET_KEY)

# CORS middleware - allows frontend from different origins to call the API
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # Allow all origins for simplicity; restrict in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("startup")
async def startup_event():
    """
    Runs when the application starts up.
    Creates all database tables if they don't exist.
    :return:
    """
    print("Starting up Wallet Service...")
    Base.metadata.create_all(bind=engine)
    print("Database tables created!")


@app.on_event("shutdown")
async def shutdown_event():
    """
    Runs when the application shuts down.
    Clean up resources if needed.
    :return:
    """
    print("Shutting down Wallet Service...")


@app.get("/")
async def root():
    """
    Health check endpoint.
    :return:
    """
    return {
        "message": "Welcome to Wallet Service API!",
        "status": "healthy",
        "version": "1.0.0"
    }

@app.get("/health")
async def health_check():
    """
    Health check endpoint.
    :return:
    """
    return {
        "status": "healthy",
        "database": "connected",
        "app_name": settings.APP_NAME
    }

# Import and include API routers
from app.api import auth, wallet

app.include_router(auth.router)
app.include_router(wallet.router)