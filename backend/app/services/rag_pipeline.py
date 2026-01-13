import re
from typing import Optional, List, Dict, Any
from langchain_community.vectorstores import Chroma
from langchain_core.embeddings import Embeddings

from app.core.config import CHROMA_DIR_STR, COLLECTION_NAME
from app.core.embedding_model import EmbeddingModel

class E5EmbeddingAdapter(Embeddings):
    def __init__(self):
        self.model = EmbeddingModel() 
    def embed_documents(self, texts): return self.model.encode(texts, is_query=False)
    def embed_query(self, text): return self.model.encode_query(text)

class RAGPipeline:
    def __init__(self):
        print(f"🔌 Loading Vector Database from: {CHROMA_DIR_STR}")
        self.vector_store = Chroma(
            persist_directory=CHROMA_DIR_STR,
            embedding_function=E5EmbeddingAdapter(),
            collection_name=COLLECTION_NAME
        )

    def detect_intent(self, query: str) -> Dict[str, Any]:
        q = query.upper()
        
        # 1. Detect Program Code
        code_match = re.search(r'\b[A-Z]{2,4}\s?\d{3,4}\b', q)
        detected_code = code_match.group(0).replace(" ", "") if code_match else None

        # 2. Detect Level
        detected_level = None
        if any(x in q for x in ["DEGREE", "SARJANA MUDA", "IJAZAH", "BACHELOR"]):
            detected_level = "Degree"
        elif any(x in q for x in ["DIPLOMA", "DIP"]):
            detected_level = "Diploma"

        # 3. Detect Category
        categories = []
        keywords = {
            "SPM": ["SPM", "FORM 5"],
            "STPM": ["STPM", "FORM 6"],
            "MATRIKULASI": ["MATRIK", "ASASI", "FOUNDATION"],
            "DIPLOMA": ["LEPASAN DIPLOMA", "PENERAPAN"],
            "APEL": ["APEL", "PENGALAMAN KERJA"]
        }
        for cat, synonyms in keywords.items():
            if any(s in q for s in synonyms):
                categories.append(cat)

        return {
            "code": detected_code,
            "level": detected_level,
            "categories": categories
        }

    def retrieve_context(self, query: str) -> str:
        intent = self.detect_intent(query)
        print(f"🔍 Intent Detected: {intent}")

        # Boost Query based on intent
        search_query = query
        if intent['code']:
            search_query = f"Kod Program {intent['code']} {query}"
        if intent['categories']:
            search_query += f" Kategori Lepasan {intent['categories'][0]}"

        print(f"🚀 Searching Chroma with: '{search_query}'")

        # --- FIX: USE MMR SEARCH FOR DIVERSITY ---
        # k=15: Fetch 15 candidates
        # fetch_k=50: Look at 50 docs initially
        # lambda_mult=0.5: Balance 50% relevance, 50% diversity
        results = self.vector_store.max_marginal_relevance_search(
            search_query,
            k=15, 
            fetch_k=50, 
            lambda_mult=0.5 
        )

        if not results:
            return ""

        # --- FIX: DEDUPLICATION LOGIC ---
        seen_codes = set()
        unique_docs = []

        for doc in results:
            content = doc.page_content
            
            # Regex to find codes like "Kod: LW224", "Code: CS110", "UE6380001"
            # This prevents showing "Law" 10 times.
            code_match = re.search(r'(?:Kod|Code|Program)[\s:]+([A-Z]{2,4}\s?\d{3}|UE\d+)', content, re.IGNORECASE)
            
            if code_match:
                # Normalize code (remove spaces) e.g., "LW 224" -> "LW224"
                found_code = code_match.group(1).replace(" ", "").upper()
                
                if found_code in seen_codes:
                    continue # Skip this doc if we already have this program
                
                seen_codes.add(found_code)
                unique_docs.append(doc)
            else:
                # If chunk has no code (maybe intro text), include it but limit count
                if len(unique_docs) < 2:
                    unique_docs.append(doc)

        # Limit to top 5 unique programs to fit LLM context window
        final_docs = unique_docs[:5]

        context_parts = []
        for doc in final_docs:
            raw_source = doc.metadata.get("source", "Unknown File")
            clean_source = raw_source.replace(".txt", "").replace(".pdf", "")
            content = doc.page_content
            
            formatted_chunk = f"--- [Reference: {clean_source}] ---\n{content}\n"
            context_parts.append(formatted_chunk)

        full_context = "\n".join(context_parts)
        return full_context

if __name__ == "__main__":
    pipeline = RAGPipeline()
    # Test with a broad query
    print(pipeline.retrieve_context("Senaraikan program yang ada"))