"""
Comprehensive test script for Wallet Service API.

Run this after setting up two test users with Google OAuth.

Usage:
    python test_wallet_api.py
"""

import requests
import json
from typing import Dict, Any

# Configuration
BASE_URL = "http://localhost:8000"

# You'll need to fill these in after OAuth login
JWT_USER_A = ""  # First user's JWT token
JWT_USER_B = ""  # Second user's JWT token


class Colors:
    """ANSI color codes for terminal output."""
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    END = '\033[0m'


def print_test(name: str):
    """Print test name."""
    print(f"\n{Colors.BLUE}▶ Testing: {name}{Colors.END}")


def print_success(message: str):
    """Print success message."""
    print(f"{Colors.GREEN}✓ {message}{Colors.END}")


def print_error(message: str):
    """Print error message."""
    print(f"{Colors.RED}✗ {message}{Colors.END}")


def print_warning(message: str):
    """Print warning message."""
    print(f"{Colors.YELLOW}⚠ {message}{Colors.END}")


def make_request(method: str, endpoint: str, jwt: str = None, api_key: str = None, data: Dict = None) -> tuple:
    """Make HTTP request with authentication."""
    url = f"{BASE_URL}{endpoint}"
    headers = {}

    if jwt:
        headers["Authorization"] = f"Bearer {jwt}"
    elif api_key:
        headers["x-api-key"] = api_key

    if data:
        headers["Content-Type"] = "application/json"

    try:
        if method == "GET":
            response = requests.get(url, headers=headers)
        elif method == "POST":
            response = requests.post(url, headers=headers, json=data)
        elif method == "DELETE":
            response = requests.delete(url, headers=headers)
        else:
            raise ValueError(f"Unsupported method: {method}")

        return response.status_code, response.json() if response.content else {}
    except requests.exceptions.RequestException as e:
        return None, {"error": str(e)}


def test_health_check():
    """Test health check endpoint."""
    print_test("Health Check")

    status, data = make_request("GET", "/health")

    if status == 200 and data.get("status") == "healthy":
        print_success("Health check passed")
        return True
    else:
        print_error(f"Health check failed: {data}")
        return False


def test_auth_me(jwt: str, user_label: str):
    """Test /auth/me endpoint."""
    print_test(f"Authentication - {user_label}")

    status, data = make_request("GET", "/auth/me", jwt=jwt)

    if status == 200 and "email" in data:
        print_success(f"{user_label} authenticated: {data['email']}")
        return data
    else:
        print_error(f"{user_label} authentication failed: {data}")
        return None


def test_wallet_details(jwt: str, user_label: str):
    """Test wallet details endpoint."""
    print_test(f"Wallet Details - {user_label}")

    status, data = make_request("GET", "/wallet/details", jwt=jwt)

    if status == 200 and "wallet_number" in data:
        print_success(f"{user_label} wallet: {data['wallet_number']}, Balance: {data['balance']}")
        return data
    else:
        print_error(f"{user_label} wallet details failed: {data}")
        return None


def test_create_api_key(jwt: str, user_label: str):
    """Test API key creation."""
    print_test(f"API Key Creation - {user_label}")

    payload = {
        "name": "test-key",
        "permissions": ["deposit", "transfer", "read"],
        "expiry": "1D"
    }

    status, data = make_request("POST", "/keys/create", jwt=jwt, data=payload)

    if status == 201 and "api_key" in data:
        print_success(f"{user_label} API key created: {data['api_key'][:20]}...")
        return data["api_key"]
    else:
        print_error(f"{user_label} API key creation failed: {data}")
        return None


def test_list_api_keys(jwt: str, user_label: str):
    """Test listing API keys."""
    print_test(f"List API Keys - {user_label}")

    status, data = make_request("GET", "/keys/list", jwt=jwt)

    if status == 200 and isinstance(data, list):
        print_success(f"{user_label} has {len(data)} API key(s)")
        return True
    else:
        print_error(f"{user_label} list API keys failed: {data}")
        return False


def test_api_key_limit(jwt: str, user_label: str):
    """Test 5-key limit enforcement."""
    print_test(f"API Key Limit (5 max) - {user_label}")

    # Try to create 6 keys
    created_keys = []
    for i in range(6):
        payload = {
            "name": f"test-key-{i}",
            "permissions": ["read"],
            "expiry": "1H"
        }
        status, data = make_request("POST", "/keys/create", jwt=jwt, data=payload)

        if status == 201:
            created_keys.append(data)
        elif i >= 5 and "Maximum" in data.get("detail", ""):
            print_success(f"5-key limit enforced correctly (rejected key #{i + 1})")
            return True

    print_error(f"Created {len(created_keys)} keys - limit not enforced!")
    return False


def test_api_key_permissions(api_key: str, user_label: str):
    """Test API key with permissions."""
    print_test(f"API Key Permissions - {user_label}")

    # Test read permission (should work)
    status, data = make_request("GET", "/wallet/balance", api_key=api_key)

    if status == 200:
        print_success(f"API key 'read' permission works: Balance = {data.get('balance')}")
        return True
    else:
        print_error(f"API key read permission failed: {data}")
        return False


def test_wallet_balance(jwt: str, user_label: str):
    """Test wallet balance endpoint."""
    print_test(f"Wallet Balance - {user_label}")

    status, data = make_request("GET", "/wallet/balance", jwt=jwt)

    if status == 200 and "balance" in data:
        print_success(f"{user_label} balance: {data['balance']}")
        return data["balance"]
    else:
        print_error(f"{user_label} balance check failed: {data}")
        return None


def test_deposit_initialization(jwt: str, user_label: str):
    """Test deposit initialization."""
    print_test(f"Deposit Initialization - {user_label}")

    payload = {"amount": 5000}
    status, data = make_request("POST", "/wallet/deposit", jwt=jwt, data=payload)

    if status == 201 and "reference" in data:
        print_success(f"{user_label} deposit initialized: {data['reference']}")
        print_warning(f"Complete payment at: {data['authorization_url'][:50]}...")
        return data["reference"]
    else:
        print_error(f"{user_label} deposit initialization failed: {data}")
        return None


def test_deposit_status(jwt: str, reference: str, user_label: str):
    """Test deposit status check."""
    print_test(f"Deposit Status Check - {user_label}")

    status, data = make_request("GET", f"/wallet/deposit/{reference}/status", jwt=jwt)

    if status == 200:
        print_success(f"{user_label} deposit status: {data['status']}")
        return data
    else:
        print_error(f"{user_label} deposit status check failed: {data}")
        return None


def test_transfer(jwt: str, recipient_wallet: str, amount: float, user_label: str):
    """Test wallet transfer."""
    print_test(f"Wallet Transfer - {user_label}")

    payload = {
        "wallet_number": recipient_wallet,
        "amount": amount
    }

    status, data = make_request("POST", "/wallet/transfer", jwt=jwt, data=payload)

    if status == 200 and data.get("status") == "success":
        print_success(f"{user_label} transferred {amount} to {recipient_wallet}")
        print_success(f"New balance: {data['sender_balance']}")
        return True
    else:
        print_error(f"{user_label} transfer failed: {data}")
        return False


def test_insufficient_balance(jwt: str, recipient_wallet: str, user_label: str):
    """Test transfer with insufficient balance."""
    print_test(f"Insufficient Balance Check - {user_label}")

    payload = {
        "wallet_number": recipient_wallet,
        "amount": 999999999
    }

    status, data = make_request("POST", "/wallet/transfer", jwt=jwt, data=payload)

    if status == 400 and "Insufficient" in data.get("detail", ""):
        print_success("Insufficient balance correctly prevented")
        return True
    else:
        print_error(f"Insufficient balance check failed: {data}")
        return False


def test_self_transfer(jwt: str, own_wallet: str, user_label: str):
    """Test self-transfer prevention."""
    print_test(f"Self-Transfer Prevention - {user_label}")

    payload = {
        "wallet_number": own_wallet,
        "amount": 100
    }

    status, data = make_request("POST", "/wallet/transfer", jwt=jwt, data=payload)

    if status == 400 and "own wallet" in data.get("detail", ""):
        print_success("Self-transfer correctly prevented")
        return True
    else:
        print_error(f"Self-transfer prevention failed: {data}")
        return False


def test_transaction_history(jwt: str, user_label: str):
    """Test transaction history endpoint."""
    print_test(f"Transaction History - {user_label}")

    status, data = make_request("GET", "/wallet/transactions", jwt=jwt)

    if status == 200 and isinstance(data, list):
        print_success(f"{user_label} has {len(data)} transaction(s)")
        if len(data) > 0:
            print(f"  Latest: {data[0]['type']} - {data[0]['amount']} - {data[0]['status']}")
        return True
    else:
        print_error(f"{user_label} transaction history failed: {data}")
        return False


def run_all_tests():
    """Run all tests."""
    print(f"\n{Colors.BLUE}{'=' * 60}")
    print("🧪 WALLET SERVICE API TEST SUITE")
    print(f"{'=' * 60}{Colors.END}\n")

    if not JWT_USER_A or not JWT_USER_B:
        print_error("Please set JWT_USER_A and JWT_USER_B in the script!")
        print_warning("1. Go to http://localhost:8000/auth/google")
        print_warning("2. Login with two different Google accounts")
        print_warning("3. Copy JWT tokens and update this script")
        return

    results = []

    # Basic tests
    results.append(("Health Check", test_health_check()))

    # Authentication
    user_a = test_auth_me(JWT_USER_A, "User A")
    user_b = test_auth_me(JWT_USER_B, "User B")
    results.append(("Auth User A", user_a is not None))
    results.append(("Auth User B", user_b is not None))

    if not user_a or not user_b:
        print_error("Authentication failed. Cannot continue tests.")
        return

    # Wallet details
    wallet_a = test_wallet_details(JWT_USER_A, "User A")
    wallet_b = test_wallet_details(JWT_USER_B, "User B")
    results.append(("Wallet A Details", wallet_a is not None))
    results.append(("Wallet B Details", wallet_b is not None))

    if not wallet_a or not wallet_b:
        print_error("Wallet details failed. Cannot continue tests.")
        return

    # API Key tests
    api_key_a = test_create_api_key(JWT_USER_A, "User A")
    results.append(("API Key Creation", api_key_a is not None))
    results.append(("List API Keys", test_list_api_keys(JWT_USER_A, "User A")))
    results.append(("API Key Permissions", test_api_key_permissions(api_key_a, "User A") if api_key_a else False))
    results.append(("API Key Limit", test_api_key_limit(JWT_USER_B, "User B")))

    # Balance checks
    balance_a = test_wallet_balance(JWT_USER_A, "User A")
    balance_b = test_wallet_balance(JWT_USER_B, "User B")
    results.append(("Balance Check A", balance_a is not None))
    results.append(("Balance Check B", balance_b is not None))

    # Deposit initialization
    deposit_ref = test_deposit_initialization(JWT_USER_A, "User A")
    results.append(("Deposit Init", deposit_ref is not None))

    if deposit_ref:
        results.append(("Deposit Status", test_deposit_status(JWT_USER_A, deposit_ref, "User A") is not None))

    # Error handling tests
    results.append(("Self-Transfer Block", test_self_transfer(JWT_USER_A, wallet_a["wallet_number"], "User A")))
    results.append(("Insufficient Balance", test_insufficient_balance(JWT_USER_A, wallet_b["wallet_number"], "User A")))

    # Transfer test (only if User A has balance)
    if balance_a and balance_a > 0:
        transfer_amount = min(100, balance_a)
        results.append(
            ("Transfer A→B", test_transfer(JWT_USER_A, wallet_b["wallet_number"], transfer_amount, "User A")))
    else:
        print_warning("User A has no balance - skipping transfer test")
        print_warning("Fund User A's wallet via Paystack and re-run tests")

    # Transaction history
    results.append(("Transaction History A", test_transaction_history(JWT_USER_A, "User A")))
    results.append(("Transaction History B", test_transaction_history(JWT_USER_B, "User B")))

    # Summary
    print(f"\n{Colors.BLUE}{'=' * 60}")
    print("📊 TEST SUMMARY")
    print(f"{'=' * 60}{Colors.END}\n")

    passed = sum(1 for _, result in results if result)
    total = len(results)

    for test_name, result in results:
        status = f"{Colors.GREEN}✓ PASS{Colors.END}" if result else f"{Colors.RED}✗ FAIL{Colors.END}"
        print(f"{status} - {test_name}")

    print(f"\n{Colors.BLUE}{'=' * 60}")
    percentage = (passed / total) * 100
    color = Colors.GREEN if percentage >= 80 else Colors.YELLOW if percentage >= 60 else Colors.RED
    print(f"{color}Result: {passed}/{total} tests passed ({percentage:.1f}%){Colors.END}")
    print(f"{'=' * 60}{Colors.END}\n")


if __name__ == "__main__":
    run_all_tests()