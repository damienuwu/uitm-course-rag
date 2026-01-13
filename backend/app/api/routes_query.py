from fastapi import APIRouter, HTTPException
from app.services.rag_pipeline import RAGPipeline  # Import the Class, not the function

router = APIRouter()

# Initialize the pipeline globally. 
# This ensures the embedding model and database connection load only once when the server starts.
pipeline_service = RAGPipeline()

@router.post("/query")
async def query_endpoint(data: dict):
    query = data.get("query", "")
    
    if not query:
        return {"answer": "Please provide a query."}

    # Call the .generate_answer() method on the instance
    answer = pipeline_service.generate_answer(query)
    
    return {"answer": answer}