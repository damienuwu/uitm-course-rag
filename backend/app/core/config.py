import os
from pathlib import Path

# Base paths
BASE_DIR = Path(__file__).resolve().parent.parent.parent
DATA_DIR = BASE_DIR / "data"
CHROMA_DIR = BASE_DIR / "chroma_db"

# Ensure directories exist
DATA_DIR.mkdir(exist_ok=True)
CHROMA_DIR.mkdir(exist_ok=True)

OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama3.2:3b") 
OLLAMA_API_URL = os.getenv("OLLAMA_API_URL", "http://localhost:11434")

EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "intfloat/multilingual-e5-base")

COLLECTION_NAME = "uitm_programs"

# Convert paths to strings
CHROMA_DIR_STR = str(CHROMA_DIR)
DATA_DIR_STR = str(DATA_DIR)