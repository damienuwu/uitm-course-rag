from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api.routes_query import router as query_router

app = FastAPI(title="UiTM Course RAG Backend")

# ✅ CORS configuration
origins = [
    "http://localhost:3000",   # your Next.js dev server
    "http://127.0.0.1:3000",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,          # or ["*"] during development
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ✅ Routes
app.include_router(query_router, prefix="/api")

@app.get("/")
def home():
    return {"message": "UiTM Course RAG API is running!"}
