import warnings

warnings.filterwarnings("ignore", category=DeprecationWarning, module="slowapi")

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from slowapi.errors import RateLimitExceeded

from wallet_api.api.v1 import auth, exchanges, transactions, wallets
from wallet_api.core.security import CSRFMiddleware
from wallet_api.utils.limiter import limiter, rate_limit_handler

app = FastAPI()

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, rate_limit_handler)

app.add_middleware(CSRFMiddleware, excluded_paths=frozenset(["/api/v1/auth/register"]))
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:8000",
        "http://127.0.0.1:8000",
        "http://localhost",
        "http://127.0.0.1",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*", "X-CSRF-Token"],
    expose_headers=["*"],
)

app.include_router(auth.router, prefix="/api/v1/auth", tags=["User"])
app.include_router(wallets.router, prefix="/api/v1/wallets", tags=["Wallet"])
app.include_router(
    transactions.router, prefix="/api/v1/transactions", tags=["Transactions"]
)
app.include_router(exchanges.router, prefix="/api/v1/transactions", tags=["Exchange"])
