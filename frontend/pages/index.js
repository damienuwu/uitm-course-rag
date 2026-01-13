import ChatBox from "../components/ChatBox";

export default function Home() {
  return (
    <main className="min-h-screen bg-gray-50 dark:bg-gray-950 text-gray-900 dark:text-gray-50 p-6">
      <h1 className="text-3xl font-bold text-center mb-8">
        UiTM Course Search (RAG)
      </h1>
      <ChatBox />
      <footer className="text-center text-sm text-gray-500 mt-10">
        © {new Date().getFullYear()} UiTM Course RAG System
      </footer>
    </main>
  );
}
