"""
Debug script to inspect ChromaDB contents
Run this to see what's actually stored in your database
"""
from app.core.chroma_client import ChromaClient
from app.core.embedding_model import EmbeddingModel

def inspect_database():
    chroma = ChromaClient()
    embedder = EmbeddingModel()
    
    print("=" * 60)
    print("🔍 INSPECTING CHROMADB DATABASE")
    print("=" * 60)
    
    # Get collection info
    collection = chroma.collection
    print(f"\n📊 Collection Name: {collection.name}")
    print(f"📈 Total Documents: {collection.count()}")
    
    if collection.count() == 0:
        print("\n❌ Database is EMPTY! You need to run the ingest script first:")
        print("   python -m app.services.ingest_service")
        return
    
    # Get a sample of documents to inspect metadata
    print("\n" + "=" * 60)
    print("📋 SAMPLING DOCUMENTS (First 5)")
    print("=" * 60)
    
    # Create a dummy query to get some results
    dummy_query = embedder.encode(["diploma sains komputer"])[0]
    results = chroma.query(query_embedding=dummy_query, n_results=5, where=None)
    
    if results and results.get("metadatas"):
        metadatas = results["metadatas"][0]
        documents = results["documents"][0]
        
        for i, (meta, doc) in enumerate(zip(metadatas, documents), 1):
            print(f"\n--- Document {i} ---")
            print(f"📄 Metadata:")
            for key, value in meta.items():
                print(f"   {key}: {value}")
            print(f"📝 Content Preview: {doc[:200]}...")
    
    # Check unique values for key fields
    print("\n" + "=" * 60)
    print("🔑 UNIQUE METADATA VALUES")
    print("=" * 60)
    
    # Get all documents (or a large sample)
    all_results = chroma.collection.get(limit=100)
    
    if all_results and all_results.get("metadatas"):
        metadatas = all_results["metadatas"]
        
        # Collect unique values
        program_levels = set()
        program_names = set()
        chunk_types = set()
        
        for meta in metadatas:
            if "program_level" in meta:
                program_levels.add(meta["program_level"])
            if "program_name" in meta:
                program_names.add(meta["program_name"])
            if "chunk_type" in meta:
                chunk_types.add(meta["chunk_type"])
        
        print(f"\n📊 Unique Program Levels ({len(program_levels)}):")
        for level in sorted(program_levels):
            print(f"   - {level}")
        
        print(f"\n📚 Unique Program Names ({len(program_names)}):")
        for name in sorted(program_names)[:10]:  # Show first 10
            print(f"   - {name}")
        if len(program_names) > 10:
            print(f"   ... and {len(program_names) - 10} more")
        
        print(f"\n📦 Unique Chunk Types ({len(chunk_types)}):")
        for chunk_type in sorted(chunk_types):
            print(f"   - {chunk_type}")
    
    # Test specific query
    print("\n" + "=" * 60)
    print("🧪 TEST QUERY: Diploma Sains Komputer")
    print("=" * 60)
    
    test_query = embedder.encode(["Diploma Sains Komputer"])[0]
    
    # Test without filter
    print("\n1️⃣ Query WITHOUT filter:")
    results_no_filter = chroma.query(query_embedding=test_query, n_results=3)
    if results_no_filter and results_no_filter.get("documents"):
        print(f"   ✅ Found {len(results_no_filter['documents'][0])} results")
        if results_no_filter.get("metadatas"):
            for meta in results_no_filter["metadatas"][0]:
                print(f"   📌 {meta.get('program_name', 'N/A')} - {meta.get('program_level', 'N/A')}")
    
    # Test with filter
    print("\n2️⃣ Query WITH filter {'program_level': 'Diploma'}:")
    try:
        results_with_filter = chroma.query(
            query_embedding=test_query, 
            n_results=3,
            where={"program_level": "Diploma"}
        )
        if results_with_filter and results_with_filter.get("documents"):
            print(f"   ✅ Found {len(results_with_filter['documents'][0])} results")
            if results_with_filter.get("metadatas"):
                for meta in results_with_filter["metadatas"][0]:
                    print(f"   📌 {meta.get('program_name', 'N/A')} - {meta.get('program_level', 'N/A')}")
        else:
            print("   ❌ No results found with this filter")
    except Exception as e:
        print(f"   ❌ Error: {e}")
    
    print("\n" + "=" * 60)
    print("✅ INSPECTION COMPLETE")
    print("=" * 60)


if __name__ == "__main__":
    inspect_database()