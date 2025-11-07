UiTM RAG Course Search System

A Retrieval-Augmented Generation (RAG) web application designed to help students explore and match UiTM courses efficiently.
Built with FastAPI (Python) for the backend and Next.js (React) for the frontend.

## 🚀 Features
✅ Intelligent course recommendation using AI (RAG)  
✅ Fast, interactive web interface (Next.js)  
✅ RESTful API built with FastAPI  
✅ Modular structure for easy maintenance  
✅ Ready for deployment (frontend + backend separation)

---

🧩 Project Structure

uitm-rag/
│
├── backend/ # FastAPI backend (Python)
│ ├── app/
│ ├── data/ # Source PDF files
│ ├── embeddings/ # Stored vector database
│ ├── ingest.py # Script for document ingestion
│ ├── main.py # FastAPI app entry point
│ └── requirements.txt
│
├── frontend/ # Next.js frontend
│ ├── package.json
│ ├── next.config.js
│ └── app/ or pages/
│
├── .gitignore
└── README.md

## ⚙️ Installation Setup

### 🔹 Prerequisites
Make sure you have these installed:
- [Python 3.10+](https://www.python.org/downloads/)
- [Node.js 18+](https://nodejs.org/)
- [npm](https://www.npmjs.com/) or [Yarn](https://yarnpkg.com/)
- [Git](https://git-scm.com/)

---

🧱 Backend Setup (FastAPI + RAG Engine)

Navigate to the backend folder:

cd backend


Create and activate a virtual environment

Windows:

python -m venv venv
venv\Scripts\activate


macOS/Linux:

python3 -m venv venv
source venv/bin/activate


Install dependencies

pip install -r requirements.txt

📚 Ingest Course Files (Important!)

Before running the backend, you must ingest the UiTM course documents (PDFs)
so that embeddings and vector storage can be created.

Place your PDF files (e.g. UiTM-BUKU-SYARAT.pdf) in:

backend/data/


Run the ingestion script

python ingest.py


This script will:

Parse the PDF documents

Generate text embeddings

Store them in backend/embeddings/ (ChromaDB or vector database)

You should see output like:

✅ Ingestion complete. 1 document indexed.

🚀 Run the Backend API

Once ingestion is done, start the FastAPI server:

uvicorn app.main:app --reload --port 8000


📍 Backend running at:
http://127.0.0.1:8000

📘 API docs:
http://127.0.0.1:8000/docs

💻 Frontend Setup (Next.js)

Open a new terminal (keep backend running)

Navigate to the frontend folder:

cd frontend


Install dependencies:

npm install


or

yarn install


Run the frontend server:

npm run dev


or

yarn dev


🌐 Frontend running at:
http://localhost:3000

🔗 Connecting Frontend and Backend

In your frontend API service (e.g. frontend/utils/api.js),
ensure your backend URL is set to:

const API_BASE_URL = "http://127.0.0.1:8000";


Example query:

const response = await fetch(`${API_BASE_URL}/ask`, {
  method: "POST",
  body: JSON.stringify({ query: "What are the requirements for Diploma in Computer Science?" }),
  headers: { "Content-Type": "application