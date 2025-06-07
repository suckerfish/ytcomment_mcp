# Authentication Guide

This guide covers authentication patterns for FastMCP servers, from simple development setups to production OAuth 2.1 implementations.

## Authentication Types

### 1. No Authentication (Development Only)

For local development and testing:

```python
from fastmcp import FastMCP

mcp = FastMCP("Development Server")

@mcp.tool()
def public_tool() -> str:
    """A tool available without authentication."""
    return "This is accessible to everyone"
```

### 2. Context-Based Authentication

Access user authentication information in your tools:

```python
from fastmcp import FastMCP, Context
from fastmcp.exceptions import ToolError

mcp = FastMCP("Authenticated Server")

@mcp.tool()
async def authenticated_tool(param: str, ctx: Context) -> dict:
    """Tool that requires authentication."""
    # Access authentication info
    user_id = ctx.client_id
    scopes = ctx.scopes
    token = ctx.token
    
    # Check if user has required permissions
    if "read_data" not in scopes:
        raise ToolError("Insufficient permissions: read_data scope required")
    
    # Use user context for API calls
    result = await fetch_user_data(user_id, param)
    return {"result": result, "user_id": user_id}

async def fetch_user_data(user_id: str, param: str):
    """Fetch data specific to the authenticated user."""
    # Your API logic here
    return f"Data for user {user_id}: {param}"
```

### 3. Custom Bearer Token Authentication

For simple token-based authentication:

```python
import os
from fastmcp import FastMCP, Context
from fastmcp.exceptions import ToolError

VALID_TOKENS = {
    "user123": {"user_id": "123", "scopes": ["read", "write"]},
    "user456": {"user_id": "456", "scopes": ["read"]},
}

@mcp.tool()
async def protected_tool(ctx: Context) -> dict:
    """Tool protected by bearer token."""
    token = ctx.token
    
    if not token or token not in VALID_TOKENS:
        raise ToolError("Invalid or missing authentication token")
    
    user_info = VALID_TOKENS[token]
    return {"message": f"Hello user {user_info['user_id']}"}
```

## OAuth 2.1 Implementation (Production)

For production remote servers, implement OAuth 2.1 with PKCE:

### Required OAuth Endpoints

Create these endpoints in your server:

```python
from fastapi import FastAPI, Request
from fastmcp import FastMCP

app = FastAPI()
mcp = FastMCP("Production Server")

# 1. Protected Resource Discovery
@app.get("/.well-known/oauth-protected-resource")
async def protected_resource_metadata(request: Request):
    base_url = str(request.base_url).rstrip('/')
    return {
        "authorization_servers": [{
            "issuer": base_url,
            "authorization_endpoint": f"{base_url}/authorize",
        }]
    }

# 2. Authorization Server Metadata  
@app.get("/.well-known/oauth-authorization-server")
async def authorization_server_metadata(request: Request):
    base_url = str(request.base_url).rstrip('/')
    return {
        "issuer": base_url,
        "authorization_endpoint": f"{base_url}/authorize",
        "token_endpoint": f"{base_url}/token",
        "token_endpoint_auth_methods_supported": ["none"],
        "scopes_supported": ["read", "write", "admin"],
        "response_types_supported": ["code"],
        "response_modes_supported": ["query"],
        "grant_types_supported": ["authorization_code"],
        "code_challenge_methods_supported": ["S256"]
    }

# 3. Authorization Endpoint
@app.get("/authorize")
async def authorize():
    # Serve your login page
    return FileResponse("static/login.html")

# 4. Token Exchange Endpoint
@app.post("/token")
async def token_exchange(request: Request):
    form = await request.form()
    
    # Validate authorization code and PKCE
    code = form.get("code")
    code_verifier = form.get("code_verifier")
    
    # Your token validation logic here
    access_token = generate_access_token(code, code_verifier)
    
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "expires_in": 3600,
        "scope": "read write"
    }
```

### User Authentication Options

#### Option 1: Firebase Auth

```html
<!-- login.html -->
<script src="https://www.gstatic.com/firebasejs/9.0.0/firebase-app.js"></script>
<script src="https://www.gstatic.com/firebasejs/9.0.0/firebase-auth.js"></script>

<script>
// Initialize Firebase
const firebaseConfig = { /* your config */ };
firebase.initializeApp(firebaseConfig);

// Google Sign-In
async function signInWithGoogle() {
    const provider = new firebase.auth.GoogleAuthProvider();
    try {
        const result = await firebase.auth().signInWithPopup(provider);
        const idToken = await result.user.getIdToken();
        
        // Send token to your callback endpoint
        const params = new URLSearchParams(window.location.search);
        const callbackUrl = new URL('/callback', window.location.origin);
        
        // Forward OAuth parameters
        ['code_challenge', 'code_challenge_method', 'state', 'redirect_uri', 'client_id']
            .forEach(param => {
                if (params.get(param)) {
                    callbackUrl.searchParams.set(param, params.get(param));
                }
            });
        
        callbackUrl.searchParams.set('idToken', idToken);
        window.location.href = callbackUrl.toString();
    } catch (error) {
        console.error('Login failed:', error);
    }
}
</script>
```

#### Option 2: Auth0

```javascript
// Using Auth0 SDK
const auth0 = new auth0.WebAuth({
    domain: 'your-domain.auth0.com',
    clientID: 'your-client-id',
    redirectUri: window.location.origin + '/callback',
    responseType: 'id_token',
    scope: 'openid profile email'
});

function login() {
    auth0.authorize();
}

// Handle callback
auth0.parseHash((err, authResult) => {
    if (authResult && authResult.idToken) {
        // Process the token
        handleAuthentication(authResult.idToken);
    }
});
```

### Token Validation

Server-side token validation:

```python
import jwt
from fastmcp import Context
from fastmcp.exceptions import ToolError

async def validate_firebase_token(id_token: str) -> dict:
    """Validate Firebase ID token."""
    try:
        # Verify the token with Firebase
        decoded_token = jwt.decode(
            id_token, 
            verify=False  # Firebase handles verification
        )
        return {
            "user_id": decoded_token.get("sub"),
            "email": decoded_token.get("email"),
            "name": decoded_token.get("name")
        }
    except Exception as e:
        raise ToolError(f"Token validation failed: {str(e)}")

@mcp.tool()
async def user_profile(ctx: Context) -> dict:
    """Get current user's profile."""
    # Access token is automatically validated by FastMCP
    user_id = ctx.client_id
    scopes = ctx.scopes
    
    # Fetch user data from your database
    user_data = await get_user_from_db(user_id)
    return {
        "user": user_data,
        "permissions": scopes
    }
```

## Security Best Practices

### 1. Token Security

```python
import secrets
import hashlib
from datetime import datetime, timedelta

class TokenManager:
    def __init__(self):
        self.tokens = {}  # Use a proper database in production
    
    def generate_access_token(self, user_id: str, scopes: list) -> str:
        """Generate a secure access token."""
        token = secrets.token_urlsafe(32)
        expires_at = datetime.utcnow() + timedelta(hours=1)
        
        self.tokens[token] = {
            "user_id": user_id,
            "scopes": scopes,
            "expires_at": expires_at,
            "created_at": datetime.utcnow()
        }
        
        return token
    
    def validate_token(self, token: str) -> dict:
        """Validate and return token information."""
        token_data = self.tokens.get(token)
        
        if not token_data:
            raise ToolError("Invalid token")
        
        if datetime.utcnow() > token_data["expires_at"]:
            del self.tokens[token]
            raise ToolError("Token expired")
        
        return token_data

# Use in your tools
token_manager = TokenManager()

@mcp.tool()
async def secure_operation(ctx: Context) -> dict:
    """Perform a secure operation."""
    # Token is automatically validated by FastMCP framework
    user_id = ctx.client_id
    
    # Additional authorization checks
    if "admin" not in ctx.scopes:
        raise ToolError("Admin privileges required")
    
    return {"message": f"Secure operation completed for user {user_id}"}
```

### 2. PKCE Implementation

```python
import base64
import hashlib
import secrets

def generate_pkce_pair():
    """Generate PKCE code verifier and challenge."""
    code_verifier = base64.urlsafe_b64encode(secrets.token_bytes(32)).decode('utf-8').rstrip('=')
    code_challenge = base64.urlsafe_b64encode(
        hashlib.sha256(code_verifier.encode('utf-8')).digest()
    ).decode('utf-8').rstrip('=')
    
    return code_verifier, code_challenge

def verify_pkce(code_verifier: str, code_challenge: str) -> bool:
    """Verify PKCE code verifier against challenge."""
    calculated_challenge = base64.urlsafe_b64encode(
        hashlib.sha256(code_verifier.encode('utf-8')).digest()
    ).decode('utf-8').rstrip('=')
    
    return calculated_challenge == code_challenge
```

### 3. Rate Limiting

```python
from collections import defaultdict
from datetime import datetime, timedelta

class RateLimiter:
    def __init__(self, max_requests: int = 100, window_minutes: int = 60):
        self.max_requests = max_requests
        self.window_minutes = window_minutes
        self.requests = defaultdict(list)
    
    def is_allowed(self, user_id: str) -> bool:
        """Check if user is within rate limits."""
        now = datetime.utcnow()
        window_start = now - timedelta(minutes=self.window_minutes)
        
        # Clean old requests
        user_requests = self.requests[user_id]
        self.requests[user_id] = [req_time for req_time in user_requests if req_time > window_start]
        
        # Check limit
        if len(self.requests[user_id]) >= self.max_requests:
            return False
        
        # Add current request
        self.requests[user_id].append(now)
        return True

rate_limiter = RateLimiter()

@mcp.tool()
async def rate_limited_tool(ctx: Context) -> dict:
    """Tool with rate limiting."""
    user_id = ctx.client_id
    
    if not rate_limiter.is_allowed(user_id):
        raise ToolError("Rate limit exceeded. Please try again later.")
    
    return {"message": "Operation completed"}
```

## Testing Authentication

### Unit Tests

```python
import pytest
from fastmcp import FastMCP, Client
from fastmcp.exceptions import ToolError

@pytest.fixture
def authenticated_server():
    server = FastMCP("Test Server")
    
    @server.tool()
    async def protected_tool(ctx: Context) -> dict:
        if not ctx.client_id:
            raise ToolError("Authentication required")
        return {"user_id": ctx.client_id}
    
    return server

async def test_authenticated_tool(authenticated_server):
    # Test with valid authentication
    async with Client(authenticated_server) as client:
        # Mock authentication context
        client._auth_context = {
            "client_id": "test_user",
            "scopes": ["read"]
        }
        
        result = await client.call_tool("protected_tool", {})
        assert result[0].text == '{"user_id": "test_user"}'

async def test_unauthenticated_access(authenticated_server):
    # Test without authentication
    async with Client(authenticated_server) as client:
        with pytest.raises(Exception):
            await client.call_tool("protected_tool", {})
```

### Manual Testing

```bash
# Test OAuth endpoints
curl -X GET http://localhost:8000/.well-known/oauth-protected-resource

# Test with bearer token
curl -H "Authorization: Bearer your-token-here" \
     -X POST http://localhost:8000/mcp \
     -H "Content-Type: application/json" \
     -d '{"method": "tools/list"}'
```

## Common Authentication Issues

1. **Missing WWW-Authenticate Header**: Always include this in 401 responses
2. **PKCE Validation Errors**: Ensure proper SHA256 encoding for code challenges  
3. **Token Expiration**: Implement proper token refresh mechanisms
4. **Scope Validation**: Check scopes in your tools, not just at the server level
5. **HTTPS Required**: Always use HTTPS in production for token security

## Environment Variables

```bash
# OAuth Configuration
OAUTH_CLIENT_ID=your_client_id
OAUTH_CLIENT_SECRET=your_client_secret
OAUTH_REDIRECT_URI=https://your-app.com/callback

# Firebase (if using)
FIREBASE_PROJECT_ID=your_project_id
FIREBASE_PRIVATE_KEY="-----BEGIN PRIVATE KEY-----\n..."
FIREBASE_CLIENT_EMAIL=your_service_account@your_project.iam.gserviceaccount.com

# Auth0 (if using)
AUTH0_DOMAIN=your_domain.auth0.com
AUTH0_CLIENT_ID=your_client_id
AUTH0_CLIENT_SECRET=your_client_secret

# Token Security
JWT_SECRET_KEY=your_very_secure_secret_key_here
TOKEN_EXPIRY_HOURS=24
```

## Next Steps

- **Deployment**: See [deployment.md](deployment.md) for production deployment with authentication
- **Testing**: Check [testing.md](testing.md) for authentication testing strategies
- **Security**: Review [best-practices.md](best-practices.md) for additional security considerations