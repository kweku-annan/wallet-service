from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import get_settings
from app.database import engine, Base

settings = get_settings()

# Create FastAPI app instance
app = FastAPI(
    title=settings.APP_NAME,
    debug=settings.DEBUG,
    version="1.0.0"
)

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