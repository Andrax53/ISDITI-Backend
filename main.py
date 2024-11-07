from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .routers import steganography

app = FastAPI()

origins = [
    "http://localhost:3000",  # Добавьте адрес вашего фронтенда
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(steganography.router)
