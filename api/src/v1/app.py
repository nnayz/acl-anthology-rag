from fastapi import FastAPI

app = FastAPI(
    title="ACL Anthology RAG API",
    description="API for the ACL Anthology RAG",
    version="0.0.1",
)


@app.get("/ping")
async def ping():
    return {"message": "pong"}
