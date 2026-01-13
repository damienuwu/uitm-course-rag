import { useState, useEffect, useRef } from "react";
// Ensure path is correct based on where your api.js file is
import api from "../utils/api";

// --- NEW IMPORTS ---
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";

export default function ChatBox() {
  const [sessionId, setSessionId] = useState(null);
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const messagesEndRef = useRef(null);
  const hasInitialized = useRef(false);

  // 1. On Load: Create Session (Malay UI)
  useEffect(() => {
    async function initSession() {
      if (hasInitialized.current) return;
      hasInitialized.current = true;

      try {
        console.log("Mencipta sesi baru...");
        const res = await api.post("/sessions", { title: "Perbualan Baru" });
        setSessionId(res.data.id);
        
        setMessages([
          { role: "assistant", content: "Assalamualaikum! Saya Penasihat Akademik UiTM anda. Sila tanya saya tentang program Diploma atau Sarjana Muda." }
        ]);
      } catch (err) {
        console.error("Gagal menyambung ke backend:", err);
        setMessages([
            { role: "assistant", content: "⚠️ Ralat: Tidak dapat menyambung ke pelayan. Pastikan backend Python sedang berjalan." }
        ]);
      }
    }
    
    initSession();
  }, []);

  // Auto-scroll
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  const sendMessage = async (e) => {
    e.preventDefault();
    if (!input.trim()) return;
    
    if (!sessionId) {
        alert("Sesi belum dimulakan. Sila refresh halaman.");
        return;
    }

    const userText = input;
    setInput("");
    
    setMessages((prev) => [...prev, { role: "user", content: userText }]);
    setLoading(true);

    try {
      const res = await api.post("/chat", {
        session_id: sessionId,
        query: userText,
      });

      // Handle response content safely
      const aiContent = res.data.content || res.data.response || ""; 

      setMessages((prev) => [...prev, { role: "assistant", content: aiContent }]);
    } catch (error) {
      console.error("Ralat Chat:", error);
      setMessages((prev) => [...prev, { role: "assistant", content: "⚠️ Maaf, berlaku ralat semasa memproses permintaan anda." }]);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="max-w-3xl mx-auto bg-white dark:bg-gray-900 rounded-xl shadow-lg overflow-hidden flex flex-col h-[600px]">
      
      {/* Messages Area */}
      <div className="flex-1 overflow-y-auto p-4 space-y-4">
        {messages.map((msg, idx) => (
          <div key={idx} className={`flex ${msg.role === "user" ? "justify-end" : "justify-start"}`}>
            <div
              className={`max-w-[85%] rounded-lg p-4 text-sm leading-relaxed shadow-sm ${
                msg.role === "user"
                  ? "bg-blue-600 text-white"
                  : "bg-gray-100 dark:bg-gray-800 text-gray-800 dark:text-gray-100 border border-gray-200 dark:border-gray-700"
              }`}
            >
              {/* --- MARKDOWN RENDERER STARTS HERE --- */}
              {msg.role === "assistant" ? (
                <ReactMarkdown
                  remarkPlugins={[remarkGfm]}
                  components={{
                    // Robust component mapping to avoid errors
                    strong: ({node, ...props}) => <span className="font-bold" {...props} />,
                    ul: ({node, ...props}) => <ul className="list-disc ml-5 space-y-1 my-2" {...props} />,
                    ol: ({node, ...props}) => <ol className="list-decimal ml-5 space-y-1 my-2" {...props} />,
                    li: ({node, ...props}) => <li className="pl-1" {...props} />,
                    p: ({node, ...props}) => <p className="mb-2 last:mb-0" {...props} />,
                    h1: ({node, ...props}) => <h1 className="text-xl font-bold my-2" {...props} />,
                    h2: ({node, ...props}) => <h2 className="text-lg font-bold my-2" {...props} />,
                  }}
                >
                  {/* Ensure content is always a string to prevent crashes */}
                  {String(msg.content)}
                </ReactMarkdown>
              ) : (
                msg.content
              )}
              {/* --- MARKDOWN RENDERER ENDS HERE --- */}
            </div>
          </div>
        ))}
        {loading && (
          <div className="flex justify-start">
            <div className="bg-gray-100 dark:bg-gray-800 p-3 rounded-lg text-sm text-gray-500 animate-pulse">
              Sedang berfikir...
            </div>
          </div>
        )}
        <div ref={messagesEndRef} />
      </div>

      {/* Input Area */}
      <form onSubmit={sendMessage} className="p-4 border-t border-gray-200 dark:border-gray-800 bg-gray-50 dark:bg-gray-900">
        <div className="flex gap-2">
          <input
            type="text"
            className="flex-1 p-3 rounded-lg border border-gray-300 dark:border-gray-700 bg-white dark:bg-gray-800 focus:ring-2 focus:ring-blue-500 outline-none text-gray-900 dark:text-white"
            placeholder="Tanya tentang syarat kemasukan, kod program..."
            value={input}
            onChange={(e) => setInput(e.target.value)}
            disabled={loading}
          />
          <button
            type="submit"
            disabled={loading}
            className="bg-blue-600 hover:bg-blue-700 text-white px-6 py-2 rounded-lg font-medium transition-colors disabled:opacity-50"
          >
            Hantar
          </button>
        </div>
      </form>
    </div>
  );
}