"""
Comprehensive tests for /auth/google endpoint.

This module tests the Google OAuth2 login flow initiation endpoint.
"""
import pytest
from unittest.mock import patch
from fastapi import status


class TestGoogleLoginEndpoint:
    """
    Test suite for /auth/google endpoint.
    
    These tests focus on the validation and error handling logic
    that can be tested without actually calling Google's OAuth service.
    """

    def test_google_login_missing_client_id(self, client, mock_settings_no_client_id):
        """
        Test that /auth/google returns 500 error when GOOGLE_CLIENT_ID is not configured.
        
        Error case - validates proper error handling when OAuth credentials are missing.
        """
        with patch("app.api.auth.settings", mock_settings_no_client_id):
            response = client.get("/auth/google")
            
            # Should return 500 Internal Server Error
            assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
            
            # Verify error message mentions missing credentials
            assert "detail" in response.json()
            error_detail = response.json()["detail"]
            assert "Google OAuth credentials are not configured" in error_detail
            assert ("GOOGLE_CLIENT_ID" in error_detail or "GOOGLE_CLIENT_SECRET" in error_detail)

    def test_google_login_missing_client_secret(self, client, mock_settings_no_client_secret):
        """
        Test that /auth/google returns 500 error when GOOGLE_CLIENT_SECRET is not configured.
        
        Error case - validates proper error handling when OAuth secret is missing.
        """
        with patch("app.api.auth.settings", mock_settings_no_client_secret):
            response = client.get("/auth/google")
            
            # Should return 500 Internal Server Error
            assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
            
            # Verify error message mentions missing credentials
            assert "detail" in response.json()
            error_detail = response.json()["detail"]
            assert "Google OAuth credentials are not configured" in error_detail
            assert ("GOOGLE_CLIENT_SECRET" in error_detail or "GOOGLE_CLIENT_ID" in error_detail)

    def test_google_login_endpoint_accepts_get_only(self, client):
        """
        Test that /auth/google only accepts GET requests.
        
        This verifies the endpoint configuration - POST, PUT, DELETE should not be allowed.
        """
        # Try POST request
        response = client.post("/auth/google")
        assert response.status_code == status.HTTP_405_METHOD_NOT_ALLOWED
        
        # Try PUT request
        response = client.put("/auth/google")
        assert response.status_code == status.HTTP_405_METHOD_NOT_ALLOWED
        
        # Try DELETE request
        response = client.delete("/auth/google")
        assert response.status_code == status.HTTP_405_METHOD_NOT_ALLOWED

    def test_google_login_missing_both_credentials(self, client):
        """
        Test with both credentials missing.
        
        Ensures the endpoint validates credentials before attempting OAuth.
        """
        mock_settings_no_creds = type('obj', (object,), {
            'GOOGLE_CLIENT_ID': '',
            'GOOGLE_CLIENT_SECRET': '',
            'GOOGLE_REDIRECT_URI': 'http://localhost:8000/auth/google/callback',
            'SECRET_KEY': 'test-secret',
            'DATABASE_URL': 'sqlite:///./test.db',
            'ALGORITHM': 'HS256',
            'ACCESS_TOKEN_EXPIRE_MINUTES': 30,
            'PAYSTACK_SECRET_KEY': 'test',
            'PAYSTACK_PUBLIC_KEY': 'test',
            'PAYSTACK_WEBHOOK_URL': 'http://test',
            'APP_NAME': 'Test',
            'DEBUG': True
        })()
        
        with patch("app.api.auth.settings", mock_settings_no_creds):
            response = client.get("/auth/google")
            
            # Should return 500 error
            assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
            assert "Google OAuth credentials are not configured" in response.json()["detail"]

    def test_google_login_validates_credentials_before_redirect(self, client, mock_settings_no_client_id):
        """
        Test that credential validation happens before attempting OAuth redirect.
        
        This ensures we fail fast with a clear error message rather than
        attempting the OAuth flow with invalid credentials.
        """
        with patch("app.api.auth.settings", mock_settings_no_client_id):
            response = client.get("/auth/google") 
            
            # Should get validation error, not OAuth error
            assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
            json_response = response.json()
            assert "detail" in json_response
            
            # Error should mention configuration, not OAuth failure
            detail = json_response["detail"]
            assert "configured" in detail.lower() or "missing" in detail.lower() or "set" in detail.lower()


class TestGoogleLoginEndpointDocumentation:
    """
    Documentation tests for the /auth/google endpoint.
    
    These tests verify that the endpoint is properly documented and discoverable.
    """
    
    def test_endpoint_exists_in_openapi_schema(self, client):
        """
        Test that the /auth/google endpoint is documented in the OpenAPI schema.
        """
        response = client.get("/openapi.json")
        assert response.status_code == status.HTTP_200_OK
        
        openapi_schema = response.json()
        assert "/auth/google" in openapi_schema["paths"]
        
    def test_endpoint_method_in_schema(self, client):
        """
        Test that the GET method is documented for /auth/google.
        """
        response = client.get("/openapi.json")
        openapi_schema = response.json()
        
        google_auth_path = openapi_schema["paths"]["/auth/google"]
        assert "get" in google_auth_path
        
    def test_endpoint_has_proper_tags(self, client):
        """
        Test that the endpoint is tagged correctly.
        """
        response = client.get("/openapi.json")
        openapi_schema = response.json()
        
        google_auth_endpoint = openapi_schema["paths"]["/auth/google"]["get"]
        assert "tags" in google_auth_endpoint
        # The auth router has tags=["Authentication"]
        assert "Authentication" in google_auth_endpoint["tags"]

