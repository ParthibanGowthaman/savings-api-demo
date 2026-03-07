from fastapi import FastAPI

from app.api.v1.accounts import router as accounts_router

app = FastAPI(title="Savings Account API", version="1.0.0")

app.include_router(accounts_router, prefix="/api/v1")


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}
