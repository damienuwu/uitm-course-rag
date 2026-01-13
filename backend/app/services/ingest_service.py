import os
import shutil
from langchain_community.vectorstores import Chroma
from langchain_core.documents import Document
from langchain_core.embeddings import Embeddings
from langchain.text_splitter import RecursiveCharacterTextSplitter

# Assumes you have these from your existing project structure
from app.core.config import CHROMA_DIR_STR, COLLECTION_NAME
from app.core.embedding_model import EmbeddingModel

# Configuration
DATA_FOLDER = "data"  # Put your 5 .txt files in this folder

class E5EmbeddingAdapter(Embeddings):
    """
    Adapts your custom EmbeddingModel to the LangChain Embeddings interface.
    """
    def __init__(self):
        self.model = EmbeddingModel() 
    
    def embed_documents(self, texts):
        # 'passage: ' prefix is often recommended for E5 models when indexing
        return self.model.encode(texts, is_query=False)
    
    def embed_query(self, text):
        # 'query: ' prefix is often recommended for E5 models when querying
        return self.model.encode_query(text)

class IngestService:
    def run(self):
        # 1. Validation
        if not os.path.exists(DATA_FOLDER):
            print(f"❌ Folder '{DATA_FOLDER}' tidak dijumpai. Sila create folder ini dan letakkan fail .txt di dalamnya.")
            return
        # 2. Setup Text Splitter
        text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=1000,
            chunk_overlap=200,   
            separators=[
                "\n================================================================================\n",
                "\n--------------------------------------------------------------------------------\n",
                "\n\n", 
                "\n", 
                " "
            ]
        )

        # 3. Process Files
        all_documents = []
        files = [f for f in os.listdir(DATA_FOLDER) if f.endswith(".txt")]
        
        print(f"📂 Menjumpai {len(files)} fail .txt dalam folder '{DATA_FOLDER}'.")

        for filename in files:
            file_path = os.path.join(DATA_FOLDER, filename)
            print(f"   Processing: {filename}...")
            
            with open(file_path, "r", encoding="utf-8") as f:
                raw_text = f.read()

            # Split text into chunks
            file_docs = text_splitter.create_documents(
                texts=[raw_text], 
                metadatas=[{"source": filename}]
            )
            
            all_documents.extend(file_docs)

        print(f"📄 Jumlah chunk dihasilkan: {len(all_documents)}")

        # 4. Ingest ke ChromaDB
        if os.path.exists(CHROMA_DIR_STR):
            shutil.rmtree(CHROMA_DIR_STR)
            print("🗑️  Database lama dipadam.")

        if all_documents:
            print(f"💾 Sedang memasukkan {len(all_documents)} dokumen ke ChromaDB...")
            
            Chroma.from_documents(
                documents=all_documents,
                embedding=E5EmbeddingAdapter(),
                persist_directory=CHROMA_DIR_STR,
                collection_name=COLLECTION_NAME
            )
            print("✅ Ingestion Selesai!")
        else:
            print("⚠️ Tiada dokumen untuk dimasukkan.")

if __name__ == "__main__":
    IngestService().run()