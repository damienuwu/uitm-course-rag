import chromadb
from chromadb.config import Settings
from typing import List, Dict, Optional, Any
from app.core.config import CHROMA_DIR_STR, COLLECTION_NAME


class ChromaClient:
    """Handles ChromaDB operations"""
    
    def __init__(self, collection_name: str = None):
        """
        Initialize ChromaDB client
        
        Args:
            collection_name: Name of the collection (default from config)
        """
        self.collection_name = collection_name or COLLECTION_NAME
        
        print(f"🗄️ Initializing ChromaDB client")
        print(f"📁 Database path: {CHROMA_DIR_STR}")
        
        # Create client with proper settings
        self.client = chromadb.PersistentClient(
            path=CHROMA_DIR_STR,  # Use string path
            settings=Settings(
                anonymized_telemetry=False,
                allow_reset=True
            )
        )
        
        # Get or create collection
        self.collection = self._get_or_create_collection()
        
        print(f"✅ ChromaDB initialized with collection: {self.collection_name}")
    
    def _get_or_create_collection(self):
        """Get existing collection or create new one"""
        try:
            # Try to get existing collection
            collection = self.client.get_collection(name=self.collection_name)
            count = collection.count()
            print(f"📚 Loaded existing collection with {count} documents")
            return collection
            
        except Exception as e:
            # Create new collection if it doesn't exist
            print(f"📝 Creating new collection: {self.collection_name}")
            return self.client.create_collection(
                name=self.collection_name,
                metadata={"description": "UiTM program information"}
            )
    
    def add_documents(
        self,
        documents: List[str],
        embeddings: List[List[float]],
        metadatas: List[Dict[str, Any]],
        ids: List[str]
    ):
        """
        Add documents to the collection
        
        Args:
            documents: List of document texts
            embeddings: List of embedding vectors
            metadatas: List of metadata dicts
            ids: List of document IDs
        """
        try:
            self.collection.add(
                documents=documents,
                embeddings=embeddings,
                metadatas=metadatas,
                ids=ids
            )
            print(f"✅ Added {len(documents)} documents to collection")
            
        except Exception as e:
            print(f"❌ Error adding documents: {e}")
            raise
    
    def query(
        self,
        query_embedding: List[float],
        n_results: int = 5,
        where: Optional[Dict[str, Any]] = None,
        where_document: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Query the collection
        
        Args:
            query_embedding: Query embedding vector
            n_results: Number of results to return
            where: Metadata filter
            where_document: Document content filter
            
        Returns:
            Query results dictionary
        """
        try:
            results = self.collection.query(
                query_embeddings=[query_embedding],
                n_results=n_results,
                where=where,
                where_document=where_document
            )
            return results
            
        except Exception as e:
            print(f"❌ Error querying collection: {e}")
            raise
    
    def get_collection_stats(self) -> Dict[str, Any]:
        """Get statistics about the collection"""
        try:
            count = self.collection.count()
            return {
                "name": self.collection_name,
                "count": count,
                "path": CHROMA_DIR_STR
            }
        except Exception as e:
            print(f"❌ Error getting stats: {e}")
            return {"error": str(e)}
    
    def delete_collection(self):
        """Delete the collection"""
        try:
            self.client.delete_collection(name=self.collection_name)
            print(f"🗑️ Deleted collection: {self.collection_name}")
        except Exception as e:
            print(f"❌ Error deleting collection: {e}")
            raise
    
    def reset_collection(self):
        """Reset the collection (delete and recreate)"""
        try:
            self.delete_collection()
            self.collection = self._get_or_create_collection()
            print(f"🔄 Reset collection: {self.collection_name}")
        except Exception as e:
            print(f"❌ Error resetting collection: {e}")
            raise


# Convenience functions
def get_chroma_client(collection_name: str = None) -> ChromaClient:
    """Get a ChromaDB client instance"""
    return ChromaClient(collection_name)


def reset_chroma_db():
    """Reset the ChromaDB database"""
    client = get_chroma_client()
    client.reset_collection()