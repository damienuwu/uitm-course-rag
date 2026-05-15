# UiTM RAG Course Search System

A Retrieval-Augmented Generation (RAG) web application designed to help students explore and match UiTM courses efficiently. Built with **FastAPI (Python)** for the backend and **Next.js (React)** for the frontend.

---

## 🚀 Features

✅ Intelligent course recommendation using AI (RAG)  
✅ Fast, interactive web interface (Next.js)  
✅ RESTful API built with FastAPI  
✅ Modular structure for easy maintenance  
✅ Ready for deployment (frontend + backend separation)

---

## ⚙️ Installation & Setup

### 🔹 Prerequisites

Make sure you have these installed:

- [Python 3.10+](https://www.python.org/downloads/)
- [Node.js 18+](https://nodejs.org/)
- [npm](https://www.npmjs.com/)
- [Git](https://git-scm.com/)

---

## 🧱 Backend Setup (FastAPI + RAG Engine)

### 1. Navigate to the backend folder

```bash
cd backend
```

### 2. Create and activate a virtual environment

**Windows:**
```bash
python -m venv venv
venv\Scripts\activate
```

**macOS/Linux:**
```bash
python3 -m venv venv
source venv/bin/activate
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

---

## 📚 Ingest Course Files (Important!)

Before running the backend, you must ingest the UiTM course documents (PDFs) so that embeddings and vector storage can be created.

### 1. Place your PDF files in:

```
backend/data/
```

> Example: `UiTM-BUKU-SYARAT.pdf`

### 2. Run the ingestion script

```bash
python -m app.services.ingest_service
```

This script will:
- Parse the PDF documents
- Generate text embeddings
- Store them in `backend/embeddings/` (ChromaDB or vector database)

You should see output like:

```
✅ Ingestion complete. 1 document indexed.
```

---

## 🚀 Run the Backend API

Once ingestion is done, start the FastAPI server:

```bash
uvicorn app.main:app --reload --port 8000
```

| Resource | URL |
|---|---|
| 📍 Backend API | http://127.0.0.1:8000 |
| 📘 API Docs (Swagger) | http://127.0.0.1:8000/docs |

---

## 💻 Frontend Setup (Next.js)

### 1. Open a new terminal (keep the backend running)

### 2. Navigate to the frontend folder

```bash
cd frontend
```

### 3. Install dependencies

```bash
npm install
```

### 4. Run the frontend server

```bash
npm run dev
```

🌐 **Frontend running at:** http://localhost:3000

---

## 🛠️ Debugging & Diagnostics

If you encounter issues or want to inspect the system state, you can use these utility scripts (run from the `backend` directory):

| Script | Command | Purpose |
|---|---|---|
| 🔍 **Inspect Database** | `python -m app.inspect_db` | View the contents of the ChromaDB vector store. |
| 🛠️ **Diagnostic Script** | `python -m app.diagnostic_script` | Run system-wide checks for connectivity and RAG health. |
| 📊 **Visualize** | `python -m app.visualize` | Generate visualizations of the RAG pipeline or data. |

---

## 🔗 Connecting Frontend and Backend

In your frontend API service (e.g. `frontend/utils/api.js`), ensure your backend URL is set to:

```js
const API_BASE_URL = "http://127.0.0.1:8000";
```

### Example query:

```js
const response = await fetch(`${API_BASE_URL}/ask`, {
  method: "POST",
  body: JSON.stringify({ query: "What are the requirements for Diploma in Computer Science?" }),
  headers: { "Content-Type": "application/json" },
});
```