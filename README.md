# Wallet Service - Backend API

A production-ready wallet service with Paystack payment integration, Google OAuth authentication, and API key management for service-to-service access.

## 🚀 Features

- ✅ **Google OAuth Authentication** - Secure user login with JWT tokens
- ✅ **Paystack Integration** - Deposit funds via Paystack payment gateway
- ✅ **Wallet System** - Auto-generated wallets with unique 13-digit numbers
- ✅ **Wallet Transfers** - Send money between users
- ✅ **API Keys** - Service-to-service authentication with permissions
- ✅ **Permission System** - Fine-grained access control (deposit, transfer, read)
- ✅ **API Key Limits** - Maximum 5 active keys per user
- ✅ **Key Expiry** - Time-based key rotation (1H, 1D, 1M, 1Y)
- ✅ **Webhook Handler** - Secure Paystack webhook processing
- ✅ **Transaction History** - Complete audit trail
- ✅ **Idempotency** - Prevents duplicate transactions
- ✅ **Atomic Transfers** - All-or-nothing operations

---

## 📋 Prerequisites

- Python 3.10+
- PostgreSQL 12+
- Google OAuth credentials
- Paystack account (test mode)
- uv package manager

---

## 🛠️ Installation

### 1. Clone the Repository

```bash
git clone <your-repo-url>
cd wallet-service
```

### 2. Install uv (if not installed)

```bash
# macOS/Linux
curl -LsSf https://astral.sh/uv/install.sh | sh

# Windows
powershell -c "irm https://astral.sh/uv/install.ps1 | iex"
```

### 3. Initialize Project

```bash
# Initialize uv
uv init

# Install dependencies
uv add fastapi uvicorn[standard]
uv add sqlalchemy psycopg2-binary alembic
uv add python-jose[cryptography] passlib[bcrypt] python-multipart
uv add authlib httpx requests
uv add python-dotenv pydantic-settings
```

### 4. Set Up PostgreSQL Database

```bash
# Connect to PostgreSQL
psql -U postgres

# Create database
CREATE DATABASE wallet_db;

# Exit
\q
```

### 5. Configure Environment Variables

Create a `.env` file:

```bash
# Database
DATABASE_URL=postgresql://your_username:your_password@localhost:5432/wallet_db

# JWT Secret (generate with: python -c "import secrets; print(secrets.token_urlsafe(32))")
SECRET_KEY=your-secret-key-here
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30

# Google OAuth
GOOGLE_CLIENT_ID=your-client-id.apps.googleusercontent.com
GOOGLE_CLIENT_SECRET=your-client-secret
GOOGLE_REDIRECT_URI=http://localhost:8000/auth/google/callback

# Paystack
PAYSTACK_SECRET_KEY=sk_test_your_secret_key
PAYSTACK_PUBLIC_KEY=pk_test_your_public_key

# App Settings
APP_NAME=Wallet Service
DEBUG=True
```

### 6. Set Up Google OAuth

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project
3. Enable **Google+ API**
4. Go to **Credentials** → **Create Credentials** → **OAuth 2.0 Client ID**
5. Add redirect URI: `http://localhost:8000/auth/google/callback`
6. Copy Client ID and Secret to `.env`

### 7. Set Up Paystack

1. Go to [Paystack Dashboard](https://dashboard.paystack.com/)
2. Sign up or log in
3. Go to **Settings** → **API Keys & Webhooks**
4. Copy **Test Secret Key** to `.env`
5. (Optional) Add webhook URL: `http://your-domain.com/wallet/paystack/webhook`

---

## 🚀 Running the Application

### Start the Server

```bash
uv run uvicorn app.main:app --reload
```

The API will be available at:
- **API:** http://localhost:8000
- **Interactive Docs:** http://localhost:8000/docs
- **Health Check:** http://localhost:8000/health

---

## 📖 Quick Start Guide

### 1. Authenticate with Google

Visit in your browser:
```
http://localhost:8000/auth/google
```

Save the returned JWT token.

### 2. Check Your Wallet

```bash
curl -X GET http://localhost:8000/wallet/details \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"
```

### 3. Create an API Key

```bash
curl -X POST http://localhost:8000/keys/create \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "my-service",
    "permissions": ["deposit", "transfer", "read"],
    "expiry": "1D"
  }'
```

Save the returned API key!

### 4. Deposit Funds

```bash
curl -X POST http://localhost:8000/wallet/deposit \
  -H "x-api-key: YOUR_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"amount": 5000}'
```

Complete payment at the returned URL.

### 5. Transfer Funds

```bash
curl -X POST http://localhost:8000/wallet/transfer \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "wallet_number": "RECIPIENT_WALLET_NUMBER",
    "amount": 1000
  }'
```

---

## 🧪 Testing

### Run Test Suite

1. Update `test_wallet_api.py` with JWT tokens
2. Run tests:

```bash
python test_wallet_api.py
```

### Manual Testing

Use the interactive docs:
```
http://localhost:8000/docs
```

### Test Payment Cards (Paystack)

- **Card Number:** 4084084084084081
- **CVV:** 408
- **Expiry:** Any future date
- **PIN:** 0000
- **OTP:** 123456

---

## 📁 Project Structure

```
wallet-service/
├── app/
│   ├── main.py              # FastAPI application
│   ├── database.py          # Database configuration
│   ├── api/                 # API endpoints
│   │   ├── auth.py          # Authentication routes
│   │   ├── wallet.py        # Wallet operations
│   │   └── keys.py          # API key management
│   ├── core/                # Core functionality
│   │   ├── config.py        # Settings
│   │   └── security.py      # JWT utilities
│   ├── models/              # Database models
│   │   ├── user.py
│   │   ├── wallet.py
│   │   ├── transaction.py
│   │   └── api_key.py
│   ├── schemas/             # Pydantic schemas
│   │   ├── user.py
│   │   ├── wallet.py
│   │   ├── paystack.py
│   │   ├── transfer.py
│   │   └── api_key.py
│   ├── services/            # Business logic
│   │   ├── user_service.py
│   │   ├── wallet_service.py
│   │   ├── paystack_service.py
│   │   └── api_key_service.py
│   └── middleware/          # Custom middleware
│       └── auth.py          # Authentication
├── test_wallet_api.py       # Test suite
├── .env                     # Environment variables
├── .gitignore
├── README.md
└── API_DOCUMENTATION.md
```

---

## 🔐 Security Features

- **JWT Authentication** - Secure token-based auth
- **API Key Hashing** - Keys stored as SHA256 hashes
- **Webhook Verification** - HMAC SHA512 signature validation
- **Permission System** - Fine-grained access control
- **Idempotency** - Prevents duplicate transactions
- **Atomic Operations** - Database transaction safety
- **Input Validation** - Pydantic schema validation

---

## 📊 Database Schema

### Users
- ID, email, Google ID, full name, profile picture

### Wallets
- ID, user_id, wallet_number (13 digits), balance

### Transactions
- ID, user_id, wallet_id, type, amount, status, reference

### API Keys
- ID, user_id, name, key_hash, permissions, expires_at

---

## 🚨 Common Issues

### Issue: Database connection failed
**Solution:** Check PostgreSQL is running and credentials in `.env` are correct

### Issue: Google OAuth redirect error
**Solution:** Ensure redirect URI in Google Console matches `.env` exactly

### Issue: Webhook not receiving events
**Solution:** Use ngrok to expose localhost and update Paystack webhook URL

### Issue: API key not working
**Solution:** Check key hasn't expired and has correct permissions

---

## 📝 API Documentation

See [API_DOCUMENTATION.md](./API_DOCUMENTATION.md) for complete API reference.

---

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Commit your changes
4. Push to the branch
5. Open a Pull Request

---

## 📄 License

This project is licensed under the MIT License.

---

## 🙏 Acknowledgments

- FastAPI for the excellent web framework
- Paystack for payment processing
- Google for OAuth services

---

## 📧 Contact

For questions or support, please open an issue on GitHub.

---

**Built with ❤️ using FastAPI, PostgreSQL, and modern Python best practices.**