import ChatBox from "../components/ChatBox";

export default function Home() {
  return (
    // Removed 'p-6' and added 'flex flex-col' for full-page layout
    <main className="min-h-screen bg-gray-50 dark:bg-gray-950 text-gray-900 dark:text-gray-50 flex flex-col">
      <header className="p-4 border-b border-gray-200 dark:border-gray-800 bg-white dark:bg-gray-950">
        <h1 className="text-xl font-bold text-center">
          UiTM Course Search (RAG)
        </h1>
      </header>
      
      {/* Container now takes up all available vertical space */}
      <div className="flex-1 overflow-hidden">
        <ChatBox />
      </div>

      <footer className="text-center text-xs text-gray-500 py-2 bg-gray-50 dark:bg-gray-950 border-t border-gray-200 dark:border-gray-800">
        © {new Date().getFullYear()} UiTM Course RAG System
      </footer>
    </main>
  );
}