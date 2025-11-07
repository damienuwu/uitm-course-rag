import { useState } from "react";
import api from "../utils/api";

export default function ChatBox() {
  const [query, setQuery] = useState("");
  const [answer, setAnswer] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const handleSubmit = async (e) => {
    e.preventDefault();

    if (!query.trim()) {
      setError("Sila masukkan soalan anda.");
      return;
    }

    setError(null);
    setLoading(true);
    setAnswer("");

    try {
      // ✅ Send key that matches backend Pydantic model
      const res = await api.post("/query", { query });
      setAnswer(res.data.answer || "⚠️ Tiada jawapan diterima daripada AI.");
    } catch (err) {
      setError("❌ Gagal mendapatkan respons daripada pelayan.");
      console.error("Backend error:", err.response?.data || err.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="max-w-2xl mx-auto mt-10 p-6 border rounded-xl shadow bg-white dark:bg-gray-900 dark:text-gray-100">
      <form onSubmit={handleSubmit} className="mb-4">
        <label className="block text-lg font-semibold mb-2">
          Tanya tentang kursus UiTM
        </label>
        <div className="flex gap-2">
          <input
            type="text"
            className="flex-1 border border-gray-300 dark:border-gray-700 p-2 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
            placeholder="Contoh: Apakah syarat kelayakan Diploma Komputer Sains?"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
          />
          <button
            type="submit"
            disabled={loading}
            className="bg-blue-600 text-white px-4 py-2 rounded-md hover:bg-blue-700 disabled:opacity-50"
          >
            {loading ? "Mencari..." : "Cari"}
          </button>
        </div>
      </form>

      {error && (
        <div className="bg-red-100 text-red-800 px-4 py-2 rounded mb-4">
          {error}
        </div>
      )}

      {loading && (
        <div className="text-center text-gray-500 animate-pulse">
          🔍 Sedang mencari maklumat...
        </div>
      )}

      {answer && !loading && (
        <div className="bg-gray-100 dark:bg-gray-800 p-4 rounded-md whitespace-pre-wrap">
          <strong>Jawapan:</strong>
          <p className="mt-2">{answer}</p>
        </div>
      )}
    </div>
  );
}
