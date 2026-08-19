import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from .retriever import retrieve


app = FastAPI(
    title="CardioRAG Retrieval API",
    version="1.0.0"
)


app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        origin.strip()
        for origin in os.getenv(
            "FRONTEND_URL",
            "http://localhost:3000",
        ).split(",")
        if origin.strip()
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class RetrieveRequest(BaseModel):
    query: str


@app.get("/health")
def health():
    return {
        "status": "ok"
    }


@app.post("/retrieve")
def retrieve_endpoint(
    request: RetrieveRequest
):
    return retrieve(
        request.query
    )