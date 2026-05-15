import { useState, useEffect, useRef } from "react";
import api from "../utils/api";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";

export default function ChatBox() {
  const [sessionId, setSessionId] = useState(null);
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const messagesEndRef = useRef(null);
  const hasInitialized = useRef(false);

  useEffect(() => {
    async function initSession() {
      if (hasInitialized.current) return;
      hasInitialized.current = true;
      try {
        const res = await api.post("/sessions", { title: "Perbualan Baru" });
        setSessionId(res.data.id);
        setMessages([
          { role: "assistant", content: "Assalamualaikum! Saya Penasihat Akademik UiTM anda. Sila tanya saya tentang program Diploma atau Sarjana Muda." }
        ]);
      } catch (err) {
        setMessages([
            { role: "assistant", content: "⚠️ Ralat: Tidak dapat menyambung ke pelayan." }
        ]);
      }
    }
    initSession();
  }, []);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  const sendMessage = async (e) => {
    e.preventDefault();
    if (!input.trim() || loading) return;
    
    const userText = input;
    setInput("");
    setMessages((prev) => [...prev, { role: "user", content: userText }]);
    setLoading(true);

    try {
      const res = await api.post("/chat", { session_id: sessionId, query: userText });
      const aiContent = res.data.content || res.data.response || ""; 
      setMessages((prev) => [...prev, { role: "assistant", content: aiContent }]);
    } catch (error) {
      setMessages((prev) => [...prev, { role: "assistant", content: "⚠️ Maaf, berlaku ralat." }]);
    } finally {
      setLoading(false);
    }
  };

  return (
    // Changed: Removed 'max-w-3xl', 'rounded-xl', 'shadow-lg', and fixed height
    <div className="flex flex-col h-full w-full bg-white dark:bg-gray-900">
      
      {/* Messages Area - Now fills the scroll space */}
      <div className="flex-1 overflow-y-auto p-6 space-y-6 pb-32">
        <div className="max-w-4xl mx-auto w-full space-y-6">
          {messages.map((msg, idx) => (
            <div key={idx} className={`flex ${msg.role === "user" ? "justify-end" : "justify-start"}`}>
              <div
                className={`max-w-[85%] rounded-2xl p-4 text-sm leading-relaxed shadow-sm ${
                  msg.role === "user"
                    ? "bg-blue-600 text-white rounded-tr-none"
                    : "bg-gray-100 dark:bg-gray-800 text-gray-800 dark:text-gray-100 border border-gray-200 dark:border-gray-700 rounded-tl-none"
                }`}
              >
                {msg.role === "assistant" ? (
                  <ReactMarkdown
                    remarkPlugins={[remarkGfm]}
                    components={{
                      strong: ({node, ...props}) => <span className="font-bold" {...props} />,
                      ul: ({node, ...props}) => <ul className="list-disc ml-5 space-y-1 my-2" {...props} />,
                      li: ({node, ...props}) => <li className="pl-1" {...props} />,
                      p: ({node, ...props}) => <p className="mb-2 last:mb-0" {...props} />,
                    }}
                  >
                    {String(msg.content)}
                  </ReactMarkdown>
                ) : (
                  msg.content
                )}
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
      </div>

      {/* Input Area - Now fixed at the bottom of the screen */}
      <div className="fixed bottom-0 left-0 right-0 p-4 border-t border-gray-200 dark:border-gray-800 bg-white dark:bg-gray-950">
        <form onSubmit={sendMessage} className="max-w-4xl mx-auto flex gap-2">
          <input
            type="text"
            className="flex-1 p-4 rounded-xl border border-gray-300 dark:border-gray-700 bg-white dark:bg-gray-800 focus:ring-2 focus:ring-blue-500 outline-none text-gray-900 dark:text-white"
            placeholder="Tanya tentang syarat kemasukan, kod program..."
            value={input}
            onChange={(e) => setInput(e.target.value)}
            disabled={loading}
          />
          <button
            type="submit"
            disabled={loading}
            className="bg-blue-600 hover:bg-blue-700 text-white px-8 py-2 rounded-xl font-medium transition-colors disabled:opacity-50"
          >
            Hantar
          </button>
        </form>
        <p className="text-[10px] text-center text-gray-400 mt-2">
            RAG Assistant can make mistakes. Check official requirements.
        </p>
      </div>
    </div>
  );
}