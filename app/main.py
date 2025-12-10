from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.sessions import SessionMiddleware
from app.core.config import get_settings
from app.database import engine, Base

# Import all models to register them with SQLAlchemy
from app.models import User, Wallet, Transaction, APIKey

settings = get_settings()

# Create FastAPI app instance with OpenAPI security schemes
app = FastAPI(
    title=settings.APP_NAME,
    description="A production-ready wallet service with Paystack payment integration, Google OAuth authentication, and API key management for service-to-service access.",
    version="1.0.0",
    debug=settings.DEBUG,
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_tags=[
        {
            "name": "Authentication",
            "description": "Google OAuth authentication endpoints"
        },
        {
            "name": "API Keys",
            "description": "API key management for service-to-service access"
        },
        {
            "name": "Wallet",
            "description": "Wallet operations including deposits, transfers, and transaction history"
        }
    ],
    # Configure security schemes for Swagger UI
    swagger_ui_parameters={
        "persistAuthorization": True,
    }
)

# Add security schemes to OpenAPI schema
def custom_openapi():
    if app.openapi_schema:
        return app.openapi_schema
    
    from fastapi.openapi.utils import get_openapi
    
    openapi_schema = get_openapi(
        title=app.title,
        version=app.version,
        description=app.description,
        routes=app.routes,
    )
    
    # Add security schemes for both JWT and API Key
    openapi_schema["components"]["securitySchemes"] = {
        "Bearer": {
            "type": "http",
            "scheme": "bearer",
            "bearerFormat": "JWT",
            "description": "Enter your JWT token from Google OAuth login"
        },
        "APIKey": {
            "type": "apiKey",
            "in": "header",
            "name": "x-api-key",
            "description": "Enter your API key for service-to-service access"
        }
    }
    
    app.openapi_schema = openapi_schema
    return app.openapi_schema

app.openapi = custom_openapi

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
from app.api import auth, wallet, keys, debug

app.include_router(auth.router)
app.include_router(wallet.router)
app.include_router(keys.router)
app.include_router(debug.router)
