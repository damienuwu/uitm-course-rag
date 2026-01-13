from typing import List, Optional, Union
from sentence_transformers import SentenceTransformer
from app.core.config import EMBEDDING_MODEL

class EmbeddingModel:
    """Handles text embedding using SentenceTransformer (Optimized for E5 models)"""

    def __init__(self, model_name: str = None):
        """
        Initialize embedding model
        
        Args:
            model_name: Name of the embedding model (default from config)
        """
        self.model_name = model_name or EMBEDDING_MODEL
        print(f"🚀 Initializing embedding model: {self.model_name}")

        # ✅ Load model locally or from Hugging Face
        try:
            self.model = SentenceTransformer(self.model_name)
            print(f"✅ Successfully loaded {self.model_name}")
        except Exception as e:
            print(f"❌ Failed to load {self.model_name}: {e}")
            raise e

    def encode(self, texts: List[str], is_query: bool = False) -> List[List[float]]:
        """
        Generate embeddings for a list of texts.
        
        Args:
            texts: List of text strings to embed
            is_query: Set True if embedding a user question (adds 'query: ' prefix for E5)
            
        Returns:
            List of embedding vectors
        """
        if not texts:
            return []

        # --- E5 SPECIFIC OPTIMIZATION ---
        # E5 models perform best when you prefix text with "query: " or "passage: "
        if "e5" in self.model_name.lower():
            prefix = "query: " if is_query else "passage: "
            # Only add prefix if it's not already there
            texts = [f"{prefix}{t}" if not t.startswith(prefix) else t for t in texts]

        try:
            # SentenceTransformer handles batching automatically
            embeddings = self.model.encode(
                texts,
                convert_to_numpy=True,
                normalize_embeddings=True
            )
            return embeddings.tolist()
        except Exception as e:
            print(f"❌ Error generating embeddings: {e}")
            # Return zero vector fallback (768 dimensions is standard for E5-base)
            return [[0.0] * 768 for _ in texts]

    def encode_query(self, query: str) -> List[float]:
        """
        Generate embedding for a single query (User Question)
        
        Args:
            query: Query text string
            
        Returns:
            Embedding vector
        """
        # We pass is_query=True to trigger the 'query: ' prefix logic
        embeddings = self.encode([query], is_query=True)
        return embeddings[0] if embeddings else [0.0] * 768

# ✅ Convenience function
def get_embeddings(texts: List[str], model_name: str = None) -> List[List[float]]:
    """
    Convenience function to generate embeddings
    
    Args:
        texts: List of texts to embed
        model_name: Optional model name override
        
    Returns:
        List of embedding vectors
    """
    embedder = EmbeddingModel(model_name)
    return embedder.encode(texts)