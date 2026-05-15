import os
os.environ["ANONYMIZED_TELEMETRY"] = "False"

from fastapi import FastAPI, Depends, APIRouter
from fastapi.middleware.cors import CORSMiddleware
from sqlmodel import Session, select, SQLModel, Field, create_engine
from typing import Optional
from datetime import datetime
from pydantic import BaseModel

from app.services.rag_pipeline import RAGPipeline
from app.core.ollama_client import query_ollama

# --- DATABASE SETUP ---
sqlite_file_name = "chat_history.db"
sqlite_url = f"sqlite:///{sqlite_file_name}"
engine = create_engine(sqlite_url)

class ChatSession(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    title: str
    created_at: datetime = Field(default_factory=datetime.utcnow)

class ChatMessage(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    session_id: int = Field(foreign_key="chatsession.id")
    role: str
    content: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)

SQLModel.metadata.create_all(engine)

def get_session():
    with Session(engine) as session: yield session

# --- API CONFIGURATION ---
app = FastAPI(title="UiTM Course Assistant RAG")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

rag = RAGPipeline()
router = APIRouter(prefix="/api")

class SessionCreate(BaseModel): title: str = "New Chat"
class QueryRequest(BaseModel): session_id: int; query: str

# --- ROUTES ---
@router.post("/sessions")
def create_chat_session(session_data: SessionCreate, db: Session = Depends(get_session)):
    session = ChatSession(title=session_data.title)
    db.add(session); db.commit(); db.refresh(session)
    return session

@router.get("/sessions")
def get_chat_sessions(db: Session = Depends(get_session)):
    return db.exec(select(ChatSession).order_by(ChatSession.created_at.desc())).all()

@router.get("/history/{session_id}")
def get_chat_history(session_id: int, db: Session = Depends(get_session)):
    return db.exec(select(ChatMessage).where(ChatMessage.session_id == session_id).order_by(ChatMessage.timestamp)).all() or []

# --- HELPER FUNCTIONS ---
def detect_language(query: str) -> str:
    malay_keywords = ["syarat", "kelayakan", "boleh", "tak", "macam", "mana", "apa", "uitm", "lepasan", "asasi", "matrik", "terima", "kasih", "sama", "minat", "suka", "layak"]
    lang = "MALAY" if any(k in query.lower() for k in malay_keywords) else "ENGLISH"
    # LOG FOR TC-01
    print(f"DEBUG [TC-01]: Language Detected: {lang}") 
    return lang

def is_conversational(query: str) -> bool:
    triggers = ["hi", "hello", "assalamualaikum", "salam", "terima kasih", "thanks", "tq", "thank you", "baik", "okay", "ok", "bye"]
    clean_q = query.strip().lower()
    result = clean_q in triggers or (len(clean_q.split()) < 5 and any(t in clean_q for t in triggers))
    # LOG FOR TC-05
    if result:
        print(f"DEBUG [TC-05]: Conversational Intent detected for query: '{query}'. Bypassing RAG.")
    return result

# --- MAIN CHAT LOGIC ---
@router.post("/chat")
def chat_endpoint(request: QueryRequest, db: Session = Depends(get_session)):
    db.add(ChatMessage(session_id=request.session_id, role="user", content=request.query))
    db.commit()

    q = request.query.strip()
    language = detect_language(q)

    # 1. CONVERSATIONAL CHECK
    if is_conversational(q):
        prompt = f"""
        You are a polite UiTM Academic Advisor. User said: "{q}".
        Reply politely in {language}. Keep it short and natural. Do NOT repeat the user's text.
        """
        final_answer = query_ollama(prompt, timeout=30, temperature=0.5)

    else:
        # 2. ACADEMIC RAG
        print(f"DEBUG [TC-02]: Intent-Based Query Boosting Mode Active.")
        context = rag.retrieve_context(q) # This will trigger RAGPipeline logs for TC-02 and TC-03

        is_degree = any(k in q.upper() for k in ["DEGREE", "SARJANA MUDA", "IJAZAH", "BACHELOR"])
        
        # --- DEFINE FORMAT GUIDES ---
        degree_guide = """
        * **Kod Program:** [Code]
        * **Tempoh:** [Duration]
        * **Syarat Am:** [Universiti Requirements]
        * **Syarat MUET:** [Specific Band Required]
        * **Syarat Khas:**
          * [List requirements by Category e.g., STPM, Matriculation, Diploma]
        """

        diploma_guide = """
        * **Kod Program:** [Code]
        * **Tempoh:** [Duration]
        * **Syarat Am:** [SPM Requirements]
        * **Syarat MUET:** Tidak Diperlukan untuk Kemasukan (Not Required for Entry).
        * **Syarat Khas (Lepasan SPM):**
          * [List specific subjects and grades required]
        """

        selected_guide = degree_guide if is_degree else diploma_guide

        if context:
            # LOG FOR TC-04
            print(f"DEBUG [TC-04]: Applying Degree/Diploma Guide formatting to LLM Prompt.")
            prompt = f"""
            You are an expert Academic Advisor for UiTM. 
            
            ### OFFICIAL CONTEXT:
            {context}
            
            ### USER QUERY:
            "{request.query}"

            ### INSTRUCTIONS:
            1. **Natural Response:** Start your answer immediately. **Do NOT** say "USER QUERY:" or "RESPONSE:". Just answer naturally.
            2. **Language:** Answer strictly in {language}.
            3. **No Filenames:** Do not mention source files.
            4. **Diploma vs Degree:**
               - If DIPLOMA, state MUET is "Tidak diperlukan untuk kemasukan".
               - If DEGREE, extract MUET Band from context.
            5. **Accuracy:** Stick to the context provided.
            6. **Recommendations:** If the user expresses interest (e.g. "I like math"), ignore the strict table format. Instead, list the relevant programs found in the context naturally and explain why they fit.
            7. **Formatting:** - If asking for a specific course (e.g. "Syarat CS110"), use this format:
                 {selected_guide}
               - If general/recommendation, use bullet points.
            """
        else:
            # LOG FOR TC-06
            print(f"DEBUG [TC-06]: No relevant documents found in ChromaDB. Using Fallback Response.")
            prompt = f"""
            You are a helpful AI Assistant. User asked: "{request.query}".
            I found no specific UiTM documents. 
            Answer generally in {language}. Do NOT repeat the user query.
            """

        final_answer = query_ollama(prompt, timeout=120, temperature=0.3)

    db.add(ChatMessage(session_id=request.session_id, role="assistant", content=final_answer))
    db.commit()

    # LOG FOR TC-07
    print(f"DEBUG [TC-07]: Returning JSON payload. Status: Success.")
    return {"role": "assistant", "content": final_answer}

app.include_router(router)