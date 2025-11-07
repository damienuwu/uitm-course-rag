from typing import List
from sentence_transformers import SentenceTransformer
from app.core.config import EMBEDDING_MODEL


class EmbeddingModel:
    """Handles text embedding using SentenceTransformer (E5 or BGE models)"""

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

    def encode(self, texts: List[str]) -> List[List[float]]:
        """
        Generate embeddings for a list of texts
        
        Args:
            texts: List of text strings to embed
            
        Returns:
            List of embedding vectors
        """
        if not texts:
            return []

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
            return [[0.0] * 768 for _ in texts]  # Default fallback dimension

    def encode_query(self, query: str) -> List[float]:
        """
        Generate embedding for a single query
        
        Args:
            query: Query text string
            
        Returns:
            Embedding vector
        """
        embeddings = self.encode([query])
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
