from fastapi import APIRouter
from app.services.rag_pipeline import generate_answer

router = APIRouter()

@router.post("/query")
async def query_endpoint(data: dict):
    query = data.get("query", "")
    answer = generate_answer(query)
    return {"answer": answer}
