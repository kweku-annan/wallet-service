from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import RedirectResponse, JSONResponse
from sqlalchemy.orm import Session
from authlib.integrations.starlette_client import OAuth
from starlette.requests import Request
from app.database import get_db
from app.core.config import get_settings
from app.core.security import create_access_token
from app.middleware.auth import get_current_user
from app.services.user_service import UserService
from app.models.user import User
from app.schemas.user import UserCreate, TokenResponse, UserResponse
from urllib.parse import urlencode

# Load settings
settings = get_settings()

# Create router
router = APIRouter(prefix="/auth", tags=["Authentication"])

# Configure OAuth client
oauth = OAuth()
oauth.register(
    name='google',
    client_id=settings.GOOGLE_CLIENT_ID,
    client_secret=settings.GOOGLE_CLIENT_SECRET,
    server_metadata_url="https://accounts.google.com/.well-known/openid-configuration",
    client_kwargs={
        'scope': 'openid email profile'
    }
)

@router.get("/google")
async def google_login(request: Request):
    """
    Initiate Google OAuth2 login flow.

    This endpoint redirects the user to Google's login page
    After successful login, Google will redirect back to /auth/google/callback

    :param request: Request object
    :return: Redirect to Google's OAuth2 authorization URL
    """
    # Validate OAuth credentials are configured
    if not settings.GOOGLE_CLIENT_ID or not settings.GOOGLE_CLIENT_SECRET:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Google OAuth credentials are not configured. Please set GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET in .env file"
        )

    redirect_uri = settings.GOOGLE_REDIRECT_URI

    # Redirect to Google OAuth
    return await oauth.google.authorize_redirect(request, redirect_uri)


@router.get("/google/callback")
async def google_callback(request: Request, db: Session = Depends(get_db)):
    """
    Google OAuth2 callback endpoint.

    This is where Google redirects the user after successful login.
    It:
    1. Receive the authorization code from Google.
    2. Exchange it for user info.
    3. Create or get existing user
    4. Generate JWT token
    5. Return token to client (via redirect or JSON based on request)

    :param request:
    :param db:
    :return: TokenResponse containing JWT token and user info OR redirect to frontend
    """
    try:
        # Get the authorization token from Google
        token = await oauth.google.authorize_access_token(request)

        # Get user info from Google
        user_info = token.get('userinfo')
        if not user_info:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Failed to retrieve user info from Google."
            )

        # Extract user data
        google_id = user_info.get('sub')  # Google's unique user ID
        email = user_info.get('email')
        full_name = user_info.get('name')
        profile_picture = user_info.get('picture')

        if not google_id or not email:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Incomplete user info received from Google."
            )

        # Create user data schema
        user_data = UserCreate(
            email=email,
            google_id=google_id,
            full_name=full_name,
            profile_picture=profile_picture
        )

        # Get or create user in database
        user, is_new = UserService.get_or_create_user(db, user_data)

        # Generate JWT token
        access_token = create_access_token(
            data = {
                "user_id": user.id,
                "email": user.email,
                "sub": user.email  # Standard JWT subject claim
            }
        )

        # Return token and user info
        return TokenResponse(
            access_token=access_token,
            token_type="bearer",
            user=UserResponse.model_validate(user)
        )

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Authentication failed: {str(e)}"
        )

@router.get("/me", response_model=UserResponse)
async def get_current_user_info(current_user: User = Depends(get_current_user)):
    """
    Get current authenticated user's info.

    This is a protected endpoint that requires a valid JWT token.
    Useful for frontend to verify token and get user details.
    :param current_user:
    :return: Current user's information
    """

    return UserResponse.model_validate(current_user)

