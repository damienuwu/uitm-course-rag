import os
from langchain_community.vectorstores import Chroma
from langchain_core.embeddings import Embeddings

# Adjusted to use your existing project core logic
from app.core.config import CHROMA_DIR_STR, COLLECTION_NAME
from app.core.embedding_model import EmbeddingModel

# We use the same Adapter as ingest_service.py for perfect compatibility
class E5EmbeddingAdapter(Embeddings):
    def __init__(self):
        self.model = EmbeddingModel() 
    
    def embed_documents(self, texts):
        return self.model.encode(texts, is_query=False)
    
    def embed_query(self, text):
        return self.model.encode_query(text)

def export_to_txt():
    EXPORT_FILENAME = "chromadb_content_export.txt"

    # 1. Validation: Check if the database directory exists
    if not os.path.exists(CHROMA_DIR_STR):
        print(f"❌ Database folder '{CHROMA_DIR_STR}' not found. Run ingest_service.py first.")
        return

    # 2. Initialize Chroma Client using the project's config
    vector_store = Chroma(
        persist_directory=CHROMA_DIR_STR,
        embedding_function=E5EmbeddingAdapter(),
        collection_name=COLLECTION_NAME
    )

    # 3. Fetch ALL data from the collection
    results = vector_store._collection.get()
    
    ids = results.get('ids', [])
    metadatas = results.get('metadatas', [])
    documents = results.get('documents', [])

    if not ids:
        print(f"⚠️ Collection '{COLLECTION_NAME}' is empty.")
        return

    print(f"📄 Exporting {len(ids)} chunks to {EXPORT_FILENAME}...")

    # 4. Write data to text file
    with open(EXPORT_FILENAME, "w", encoding="utf-8") as f:
        f.write(f"CHROMADB EXPORT: {COLLECTION_NAME}\n")
        f.write(f"TOTAL CHUNKS: {len(ids)}\n")
        f.write("=" * 50 + "\n\n")

        for i in range(len(ids)):
            f.write(f"--- ENTRY {i+1} ---\n")
            f.write(f"ID: {ids[i]}\n")
            f.write(f"SOURCE FILE: {metadatas[i].get('source', 'N/A')}\n")
            f.write(f"METADATA: {metadatas[i]}\n")
            f.write(f"CONTENT:\n{documents[i]}\n")
            f.write("\n" + "-"*30 + "\n\n")

    print(f"✅ Export complete! File location: {os.path.abspath(EXPORT_FILENAME)}")

if __name__ == "__main__":
    export_to_txt()