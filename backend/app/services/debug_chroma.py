"""
🔍 Debug Script: Inspect UiTM ChromaDB Contents
Use this to explore what data is stored in your database.
"""
from app.core.chroma_client import ChromaClient
from app.core.embedding_model import EmbeddingModel


def inspect_database():
    chroma = ChromaClient()
    embedder = EmbeddingModel()

    print("\n" + "=" * 60)
    print("🔍 INSPECTING UiTM CHROMADB DATABASE")
    print("=" * 60)

    # === 1️⃣ Collection Summary ===
    collection = chroma.collection
    print(f"\n📚 Collection Name: {collection.name}")
    
    try:
        total_docs = collection.count()
    except Exception:
        total_docs = "Unknown"
    print(f"📈 Total Documents: {total_docs}")

    if total_docs == 0 or total_docs == "Unknown":
        print("\n❌ Database is EMPTY or inaccessible!")
        print("   ➤ Run the ingestion script first:")
        print("     python -m app.services.ingest_service")
        return

    # === 2️⃣ Sample Documents ===
    print("\n" + "=" * 60)
    print("📋 SAMPLE DOCUMENTS (First 5)")
    print("=" * 60)

    try:
        dummy_query = embedder.encode(["diploma sains komputer"])[0]
        results = chroma.query(query_embedding=dummy_query, n_results=5)
    except Exception as e:
        print(f"⚠️ Error querying ChromaDB: {e}")
        return

    if not results or not results.get("metadatas"):
        print("❌ No results returned from ChromaDB.")
        return

    for i, (meta, doc) in enumerate(zip(results["metadatas"][0], results["documents"][0]), 1):
        print(f"\n--- Document {i} ---")
        print("📄 Metadata:")
        for key, value in meta.items():
            print(f"   {key}: {value}")
        print(f"📝 Content Preview: {doc[:250]}...")
        print("-" * 60)

    # === 3️⃣ Metadata Overview ===
    print("\n" + "=" * 60)
    print("🔑 UNIQUE METADATA VALUES")
    print("=" * 60)

    all_results = collection.get(limit=200)
    if not all_results or not all_results.get("metadatas"):
        print("❌ No metadata found in collection.")
        return

    metadatas = all_results["metadatas"]

    program_levels = {m.get("program_level", "N/A") for m in metadatas}
    faculties = {m.get("faculty_college", "N/A") for m in metadatas}
    chunk_types = {m.get("chunk_type", "N/A") for m in metadatas}
    program_names = {m.get("program_name", "N/A") for m in metadatas}

    print(f"\n🎓 Program Levels ({len(program_levels)}):")
    for level in sorted(program_levels):
        print(f"   - {level}")

    print(f"\n🏛️ Faculties/Colleges ({len(faculties)}):")
    for fac in sorted(faculties):
        print(f"   - {fac}")

    print(f"\n📦 Chunk Types ({len(chunk_types)}):")
    for chunk in sorted(chunk_types):
        print(f"   - {chunk}")

    print(f"\n📚 Program Names ({len(program_names)} total):")
    for name in sorted(program_names)[:10]:
        print(f"   - {name}")
    if len(program_names) > 10:
        print(f"   ... and {len(program_names) - 10} more")

    # === 4️⃣ Test Queries ===
    print("\n" + "=" * 60)
    print("🧪 TEST QUERY: Diploma Sains Komputer")
    print("=" * 60)

    try:
        test_query = embedder.encode(["Diploma Sains Komputer"])[0]
    except Exception as e:
        print(f"❌ Embedding error: {e}")
        return

    # Test 1: No filter
    print("\n1️⃣ Query WITHOUT filter:")
    try:
        no_filter = chroma.query(query_embedding=test_query, n_results=3)
        docs = no_filter.get("documents", [[]])[0]
        metas = no_filter.get("metadatas", [[]])[0]
        print(f"   ✅ Found {len(docs)} documents")
        for meta in metas:
            print(f"   📌 {meta.get('program_name', 'N/A')} - {meta.get('program_level', 'N/A')}")
    except Exception as e:
        print(f"   ❌ Error: {e}")

    # Test 2: With filter
    print("\n2️⃣ Query WITH filter {'program_level': {'$eq': 'Diploma'}}:")
    try:
        with_filter = chroma.query(
            query_embedding=test_query,
            n_results=3,
            where={"program_level": {"$eq": "Diploma"}}
        )
        docs = with_filter.get("documents", [[]])[0]
        metas = with_filter.get("metadatas", [[]])[0]
        print(f"   ✅ Found {len(docs)} documents")
        for meta in metas:
            print(f"   🎓 {meta.get('program_name', 'N/A')} - {meta.get('faculty_college', 'N/A')}")
    except Exception as e:
        print(f"   ❌ Error: {e}")

    # === 5️⃣ Final Summary ===
    print("\n" + "=" * 60)
    print("✅ INSPECTION COMPLETE")
    print("=" * 60)


if __name__ == "__main__":
    inspect_database()
