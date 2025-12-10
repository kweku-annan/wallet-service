# Wallet Service API Documentation

## Overview
A backend wallet service with Paystack integration, JWT authentication, and API key support for service-to-service access.

**Base URL:** `http://localhost:8000`

**Documentation:** `http://localhost:8000/docs` (Swagger UI)

---

## Authentication

The API supports two authentication methods:

### 1. JWT (User Authentication)
```bash
Authorization: Bearer <jwt_token>
```

### 2. API Key (Service Authentication)
```bash
x-api-key: <api_key>
```

---

## Endpoints

### **Authentication**

#### `GET /auth/google`
Initiate Google OAuth login.

**Response:** Redirects to Google login page

---

#### `GET /auth/google/callback`
OAuth callback endpoint. Returns JWT token.

**Response:**
```json
{
  "access_token": "eyJhbGc...",
  "token_type": "bearer",
  "user": {
    "id": 1,
    "email": "user@example.com",
    "full_name": "John Doe"
  }
}
```

---

#### `GET /auth/me`
Get current authenticated user.

**Auth:** JWT required

**Response:**
```json
{
  "id": 1,
  "email": "user@example.com",
  "full_name": "John Doe",
  "is_active": true
}
```

---

### **API Keys**

#### `POST /keys/create`
Create a new API key.

**Auth:** JWT required

**Request:**
```json
{
  "name": "wallet-service",
  "permissions": ["deposit", "transfer", "read"],
  "expiry": "1D"
}
```

**Expiry formats:** `1H`, `1D`, `1M`, `1Y`

**Permissions:** `deposit`, `transfer`, `read`

**Response:**
```json
{
  "api_key": "sk_live_xxxxx",
  "expires_at": "2024-12-11T12:00:00Z",
  "name": "wallet-service",
  "permissions": ["deposit", "transfer", "read"]
}
```

⚠️ **Save the API key! It's only shown once.**

---

#### `GET /keys/list`
List all API keys (without revealing actual keys).

**Auth:** JWT required

**Response:**
```json
[
  {
    "id": 1,
    "name": "wallet-service",
    "key_prefix": "sk_live_",
    "permissions": ["deposit", "transfer"],
    "expires_at": "2024-12-11T12:00:00Z",
    "is_active": true,
    "created_at": "2024-12-10T12:00:00Z"
  }
]
```

---

#### `POST /keys/rollover`
Rollover an expired API key.

**Auth:** JWT required

**Request:**
```json
{
  "expired_key_id": "123",
  "expiry": "1M"
}
```

**Response:**
```json
{
  "api_key": "sk_live_new_key_xxxxx",
  "expires_at": "2025-01-10T12:00:00Z",
  "name": "wallet-service",
  "permissions": ["deposit", "transfer"],
  "old_key_id": 123
}
```

---

#### `DELETE /keys/{key_id}`
Revoke an API key.

**Auth:** JWT required

**Response:**
```json
{
  "message": "API key revoked successfully",
  "key_id": 123
}
```

---

### **Wallet Operations**

#### `GET /wallet/balance`
Get wallet balance.

**Auth:** JWT or API key with `read` permission

**Response:**
```json
{
  "balance": 15000.0
}
```

---

#### `GET /wallet/details`
Get full wallet details.

**Auth:** JWT required

**Response:**
```json
{
  "id": 1,
  "wallet_number": "4566678954356",
  "balance": 15000.0,
  "is_active": true,
  "created_at": "2024-12-10T12:00:00Z"
}
```

---

#### `POST /wallet/deposit`
Initialize a deposit via Paystack.

**Auth:** JWT or API key with `deposit` permission

**Request:**
```json
{
  "amount": 5000
}
```

**Response:**
```json
{
  "reference": "PS_a1b2c3d4e5f6g7h8",
  "authorization_url": "https://checkout.paystack.com/...",
  "amount": 5000
}
```

**Next step:** User completes payment at `authorization_url`

---

#### `POST /wallet/paystack/webhook`
Paystack webhook endpoint (internal use).

**Note:** This endpoint is called by Paystack, not by users.

**Security:** Validates Paystack signature

**Actions:**
- Verifies webhook signature
- Credits wallet on successful payment
- Idempotent (prevents double-crediting)

---

#### `GET /wallet/deposit/{reference}/status`
Check deposit status manually.

**Auth:** JWT or API key with `read` permission

**Response:**
```json
{
  "reference": "PS_a1b2c3d4e5f6g7h8",
  "status": "success",
  "amount": 5000
}
```

**Possible statuses:** `pending`, `success`, `failed`

⚠️ **This endpoint does NOT credit wallets. Only the webhook credits wallets.**

---

#### `POST /wallet/transfer`
Transfer funds to another wallet.

**Auth:** JWT or API key with `transfer` permission

**Request:**
```json
{
  "wallet_number": "4566678954356",
  "amount": 3000
}
```

**Response:**
```json
{
  "status": "success",
  "message": "Transfer completed",
  "amount": 3000,
  "recipient_wallet_number": "4566678954356",
  "sender_balance": 12000.0
}
```

**Validations:**
- Sender must have sufficient balance
- Cannot transfer to own wallet
- Both wallets must be active
- Atomic operation (all-or-nothing)

---

#### `GET /wallet/transactions`
Get transaction history.

**Auth:** JWT or API key with `read` permission

**Query Parameters:**
- `limit` (default: 50)
- `offset` (default: 0)

**Response:**
```json
[
  {
    "type": "deposit",
    "amount": 5000,
    "status": "success"
  },
  {
    "type": "transfer",
    "amount": 3000,
    "status": "success"
  }
]
```

---

## Error Responses

All errors follow this format:

```json
{
  "detail": "Error message here"
}
```

### Common Status Codes

| Code | Meaning |
|------|---------|
| 200 | Success |
| 201 | Created |
| 400 | Bad Request (validation error) |
| 401 | Unauthorized (invalid auth) |
| 403 | Forbidden (insufficient permissions) |
| 404 | Not Found |
| 500 | Internal Server Error |

---

## Security Notes

### API Key Best Practices
- Store API keys securely
- Never commit keys to version control
- Rotate keys regularly
- Use minimum required permissions
- Revoke compromised keys immediately

### Webhook Security
- Paystack webhooks are verified via HMAC SHA512
- Invalid signatures are rejected
- Idempotency prevents duplicate processing

### Transaction Safety
- All transfers are atomic
- Balance checks prevent overdrafts
- Failed operations rollback automatically

---

## Rate Limits

- Maximum 5 active API keys per user
- No other rate limits currently enforced

---

## Testing

### Test Cards (Paystack)
- **Card:** 4084084084084081
- **CVV:** 408
- **Expiry:** Any future date
- **PIN:** 0000
- **OTP:** 123456

### Example Workflow

1. **Authenticate:**
   ```bash
   # Visit in browser
   http://localhost:8000/auth/google
   ```

2. **Create API Key:**
   ```bash
   curl -X POST http://localhost:8000/keys/create \
     -H "Authorization: Bearer YOUR_JWT" \
     -H "Content-Type: application/json" \
     -d '{"name": "test", "permissions": ["deposit", "transfer", "read"], "expiry": "1D"}'
   ```

3. **Deposit Funds:**
   ```bash
   curl -X POST http://localhost:8000/wallet/deposit \
     -H "x-api-key: YOUR_API_KEY" \
     -H "Content-Type: application/json" \
     -d '{"amount": 5000}'
   ```

4. **Transfer Funds:**
   ```bash
   curl -X POST http://localhost:8000/wallet/transfer \
     -H "Authorization: Bearer YOUR_JWT" \
     -H "Content-Type: application/json" \
     -d '{"wallet_number": "RECIPIENT_WALLET", "amount": 1000}'
   ```

---

## Support

For issues or questions, check:
- Interactive docs: `http://localhost:8000/docs`
- Health check: `http://localhost:8000/health`