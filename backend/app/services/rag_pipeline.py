from typing import Dict, List, Optional
from app.core.embedding_model import EmbeddingModel
from app.core.chroma_client import ChromaClient
from app.core.ollama_client import query_ollama
from app.services.ingest_service import (
    detect_program_level,
    detect_program_name,
    detect_qualification_type
)
import re


def deduplicate_documents(docs: List[str], threshold: float = 0.85) -> List[str]:
    """Remove duplicate or highly similar documents"""
    from difflib import SequenceMatcher
    
    if not docs:
        return []
    
    # Remove exact duplicates first
    unique_docs = list(dict.fromkeys(docs))
    
    # Remove near-duplicates
    filtered_docs = []
    for doc in unique_docs:
        is_duplicate = False
        for existing_doc in filtered_docs:
            similarity = SequenceMatcher(None, doc, existing_doc).ratio()
            if similarity > threshold:
                is_duplicate = True
                break
        
        if not is_duplicate:
            filtered_docs.append(doc)
    
    return filtered_docs


def extract_program_code_from_query(query: str) -> Optional[str]:
    """Extract program code if mentioned in query (e.g., CDCS230, CDCS255)"""
    # Match UiTM codes like CDCS230, ASAR240, etc.
    match = re.search(r'\b[A-Z]{2,4}\d{3}\b', query.upper())
    if match:
        return match.group(0)
    return None


def is_generic_program_query(query: str, program_name: str) -> bool:
    """
    Check if user is asking about generic program (e.g., "Sains Komputer") 
    vs specialized variant (e.g., "Sains Komputer Rangkaian Komputer")
    """
    if program_name in ["Unknown", "Unspecified"]:
        return False
    
    query_lower = query.lower()
    
    # Keywords that indicate comparison/difference questions
    comparison_keywords = ['perbezaan', 'beza', 'difference', 'compare', 'berbanding']
    is_comparison = any(kw in query_lower for kw in comparison_keywords)
    
    # If it's a comparison query, we want BOTH programs
    if is_comparison:
        return False
    
    # Keywords that indicate specialized/specific programs
    specialized_keywords = [
        'rangkaian', 'multimedia', 'grafik', 'digital', 'forensik',
        'sistem', 'perisian', 'mobile', 'keselamatan', 'network',
        'web', 'game', 'artificial', 'intelligence',
        'data', 'cloud', 'cyber', 'embedded', 'robotik'
    ]
    
    # If query contains specialized keywords, it's NOT a generic query
    for keyword in specialized_keywords:
        if keyword in query_lower:
            return False
    
    # If query only mentions base program name (e.g., "Sains Komputer" only)
    if program_name.lower() in query_lower:
        # Check if there are additional qualifiers after the program name
        words_after_program = query_lower.split(program_name.lower())
        if len(words_after_program) > 1:
            remaining_text = words_after_program[1].strip()
            # If there's meaningful text after, it might be specialized
            if len(remaining_text.split()) > 2:
                return False
        return True
    
    return True


def prioritize_generic_programs(docs: List[str], metadatas: List[Dict], 
                                  query: str, program_name: str) -> tuple:
    """
    Reorder results to prioritize generic programs over specialized variants
    when user asks generic questions
    """
    if not is_generic_program_query(query, program_name):
        return docs, metadatas
    
    generic_docs = []
    generic_metas = []
    specialized_docs = []
    specialized_metas = []
    
    for doc, meta in zip(docs, metadatas):
        prog_name = meta.get('program_name', '').lower()
        
        # Check if program name is exactly the base program (no extra qualifiers)
        # E.g., "Diploma Sains Komputer" vs "Diploma Sains Komputer (Rangkaian Komputer)"
        is_generic = (
            program_name.lower() in prog_name and
            len(prog_name.split()) <= len(program_name.split()) + 2  # Allow some flexibility
        )
        
        if is_generic:
            generic_docs.append(doc)
            generic_metas.append(meta)
        else:
            specialized_docs.append(doc)
            specialized_metas.append(meta)
    
    # Return generic first, then specialized
    return generic_docs + specialized_docs, generic_metas + specialized_metas


def build_smart_filter(level: str, program_name: str, qual_type: Optional[str] = None, 
                       program_code: Optional[str] = None) -> Optional[Dict]:
    """
    Build intelligent and consistent filter for ChromaDB query
    ChromaDB requires multiple conditions to be wrapped in $and/$or
    """
    conditions = []

    # If program code is explicitly mentioned, filter by it (highest priority)
    if program_code:
        return {"program_code_uitm": {"$eq": program_code}}

    # Filter by level (Diploma / Degree)
    if level and level not in ["Unspecified", "Unknown"]:
        conditions.append({"program_level": {"$eq": level}})

    # Filter by program name - use contains for flexibility
    if program_name and program_name not in ["Unknown", "Unspecified"]:
        # Extract base name without level prefix for better matching
        base_name = program_name.replace("Diploma ", "").replace("Degree ", "").strip()
        conditions.append({"program_name": {"$contains": base_name}})

    # Filter by qualification type if explicitly mentioned
    if qual_type and qual_type.upper() != "DIPLOMA":  # Don't filter by DIPLOMA type when comparing programs
        conditions.append({"requirement_type": {"$eq": qual_type.upper()}})

    # Return properly formatted filter
    if len(conditions) == 0:
        return None
    elif len(conditions) == 1:
        return conditions[0]
    else:
        return {"$and": conditions}


def format_context(docs: List[str], metadatas: List[Dict]) -> str:
    """Format retrieved documents into clean context"""
    formatted_sections = []
    
    for doc, meta in zip(docs, metadatas):
        section = f"""
--- {meta.get('program_name', 'Program')} ---
Kod: {meta.get('program_code_uitm', 'N/A')}
Tahap: {meta.get('program_level', 'N/A')}

{doc}
"""
        formatted_sections.append(section.strip())
    
    return "\n\n".join(formatted_sections)


def generate_answer(query: str, max_tokens: int = 2048, temperature: float = 0.3) -> str:
    """
    Generate answer using RAG pipeline
    
    Args:
        query: User's question in Malay or English
        max_tokens: Maximum tokens for LLM response
        temperature: LLM temperature (lower = more focused)
    
    Returns:
        Generated answer string
    """
    print("\n" + "=" * 60)
    print("🔍 RAG Pipeline Started")
    print("=" * 60)
    
    # Initialize components
    embedder = EmbeddingModel()
    chroma = ChromaClient()

    # 🧠 Detect query intent
    level = detect_program_level(query)
    program_name = detect_program_name(query)
    qual_type = detect_qualification_type(query)
    program_code = extract_program_code_from_query(query)

    print(f"📊 Query Analysis:")
    print(f"  • Program Level: {level}")
    print(f"  • Program Name: {program_name}")
    print(f"  • Qualification Type: {qual_type}")
    print(f"  • Program Code: {program_code if program_code else 'Not specified'}")
    print(f"  • Generic Query: {is_generic_program_query(query, program_name)}")

    # 🔍 Build enhanced query for embedding
    query_parts = [query]
    
    # For comparison queries, don't add level to avoid over-filtering
    comparison_keywords = ['perbezaan', 'beza', 'difference', 'compare', 'berbanding']
    is_comparison = any(kw in query.lower() for kw in comparison_keywords)
    
    if not is_comparison and level != "Unspecified":
        query_parts.append(level)
    
    if program_name != "Unknown":
        # Extract base name without level prefix
        base_name = program_name.replace("Diploma ", "").replace("Degree ", "").strip()
        query_parts.append(base_name)
    
    enhanced_query = " ".join(query_parts)
    print(f"  • Enhanced Query: {enhanced_query}")

    # 🎯 Generate query embedding
    try:
        query_embed = embedder.encode([enhanced_query])[0]
        print(f"✅ Generated query embedding")
    except Exception as e:
        print(f"❌ Embedding error: {e}")
        return "⚠️ Ralat semasa memproses pertanyaan. Sila cuba lagi."

    # 🗂️ Build filter - don't filter by level for comparison queries
    if is_comparison:
        # For comparisons, only filter by program name, not level
        where_filter = build_smart_filter("Unspecified", program_name, None, program_code)
    else:
        where_filter = build_smart_filter(level, program_name, qual_type, program_code)
    
    print(f"🔧 Filter: {where_filter}")

    # 📚 Retrieve from ChromaDB
    print(f"🔍 Querying ChromaDB...")
    try:
        results = chroma.query(
            query_embedding=query_embed,
            n_results=10,  # Get more results for comparison queries
            where=where_filter
        )
        print(f"✅ Query successful")
    except Exception as e:
        print(f"⚠️ ChromaDB query failed with filter: {e}")
        print(f"🔄 Retrying without filter...")
        try:
            results = chroma.query(
                query_embedding=query_embed,
                n_results=15
            )
            print(f"✅ Query successful without filter")
        except Exception as e2:
            print(f"❌ ChromaDB error: {e2}")
            return "⚠️ Ralat semasa mengakses pangkalan data. Sila cuba lagi."

    # ✅ Check results
    if not results or not results.get("documents") or not results["documents"][0]:
        print("❌ No relevant documents found")
        return "⚠️ Tiada maklumat relevan dijumpai dalam pangkalan data UiTM. Sila pastikan program yang anda cari wujud atau cuba soalan yang lebih spesifik."

    # 🧹 Clean and deduplicate context
    raw_docs = results["documents"][0]
    raw_metadatas = results.get("metadatas", [[]])[0]
    
    print(f"📄 Retrieved {len(raw_docs)} documents")
    
    # For comparison queries, ensure we get both program levels
    if is_comparison:
        print(f"🔄 Processing comparison query - ensuring both programs are included")
        # Group by program level
        diploma_docs = [(d, m) for d, m in zip(raw_docs, raw_metadatas) if m.get('program_level') == 'Diploma']
        degree_docs = [(d, m) for d, m in zip(raw_docs, raw_metadatas) if m.get('program_level') == 'Degree']
        
        print(f"  • Diploma documents: {len(diploma_docs)}")
        print(f"  • Degree documents: {len(degree_docs)}")
        
        # Take top results from each level
        selected_docs = []
        selected_metas = []
        
        for d, m in (diploma_docs[:3] + degree_docs[:3]):
            selected_docs.append(d)
            selected_metas.append(m)
        
        raw_docs = selected_docs
        raw_metadatas = selected_metas
        print(f"  • Selected {len(raw_docs)} documents for comparison")
    else:
        # Prioritize generic programs if needed
        if program_name not in ["Unknown", "Unspecified"]:
            raw_docs, raw_metadatas = prioritize_generic_programs(
                raw_docs, raw_metadatas, query, program_name
            )
            print(f"🎯 After prioritization (generic first)")
    
    # Deduplicate
    unique_docs = deduplicate_documents(raw_docs, threshold=0.85)
    print(f"🧹 After deduplication: {len(unique_docs)} documents")
    
    # Get corresponding metadata
    unique_metadatas = []
    for doc in unique_docs:
        try:
            idx = raw_docs.index(doc)
            if idx < len(raw_metadatas):
                unique_metadatas.append(raw_metadatas[idx])
            else:
                unique_metadatas.append({})
        except ValueError:
            unique_metadatas.append({})
    
    # Format context (use more docs for comparison queries)
    num_docs = 8 if is_comparison else 5
    context = format_context(unique_docs[:num_docs], unique_metadatas[:num_docs])
    print(f"📝 Context length: {len(context)} characters")
    
    # Print which programs are being used for context
    print(f"📚 Programs in context:")
    for meta in unique_metadatas[:num_docs]:
        print(f"  • {meta.get('program_name', 'Unknown')} ({meta.get('program_code_uitm', 'N/A')}) - {meta.get('program_level', 'N/A')}")

    # 🤖 Construct prompt
    if is_comparison:
        prompt = f"""Anda adalah Pegawai Akademik UiTM yang membantu bakal pelajar membandingkan program.

Berdasarkan maklumat rasmi dari dokumen UiTM di bawah, jawab soalan pelajar dengan lengkap dan tepat dalam Bahasa Malaysia yang formal.

=== MAKLUMAT RASMI UiTM ===
{context}

=== SOALAN PELAJAR ===
{query}

=== ARAHAN PENTING ===
1. Gunakan HANYA maklumat dari konteks di atas. Jangan reka maklumat baharu.
2. BANDINGKAN kedua-dua program dengan jelas (Diploma vs Degree/Sarjana Muda)
3. Fokus pada perbezaan utama:
   - Tempoh pengajian
   - Tahap program (Diploma vs Degree)
   - Kod program (UiTM dan UPU) - PASTIKAN KOD BETUL dari konteks
   - Syarat kemasukan (SPM, CGPA, MUET)
   - Fakulti/Kolej
   - Peluang kerjaya (jika disebutkan)
4. Gunakan format berstruktur dengan bullet points
5. Nyatakan dengan jelas program mana untuk Diploma dan mana untuk Degree
6. Elakkan pengulangan maklumat yang sama

PENTING: Pastikan kod program yang anda sebut TEPAT dengan apa yang ada dalam konteks!

Jawapan anda:"""
    else:
        prompt = f"""Anda adalah Pegawai Akademik UiTM yang membantu bakal pelajar.

Berdasarkan maklumat rasmi dari dokumen UiTM di bawah, jawab soalan pelajar dengan lengkap dan tepat dalam Bahasa Malaysia yang formal.

=== MAKLUMAT RASMI UiTM ===
{context}

=== SOALAN PELAJAR ===
{query}

=== ARAHAN PENTING ===
1. Gunakan HANYA maklumat dari konteks di atas. Jangan reka maklumat baharu.
2. Jika maklumat tidak lengkap, nyatakan dengan jelas: "Maklumat tidak tersedia dalam dokumen"
3. Jika dokumen menyebut syarat SPM, STPM, SIJIL, PRA DIPLOMA, atau APEL, senaraikan SEMUA.
4. Gunakan format berstruktur dengan bullet points untuk mudah dibaca
5. Sertakan kod program (UiTM dan UPU) jika relevan - pastikan kod yang disebut BETUL-BETUL dari konteks
6. Nyatakan keperluan CGPA dan MUET dengan jelas
7. Elakkan pengulangan maklumat yang sama
8. Gunakan Bahasa Malaysia formal dan tepat
9. Jika ada beberapa program yang serupa, bezakan dengan jelas dan sertakan kod program untuk setiap satu

PENTING: Pastikan kod program yang anda sebut TEPAT dengan apa yang ada dalam konteks!

Jawapan anda:"""

    # 🚀 Query LLM
    print(f"🤖 Querying Ollama LLM...")
    try:
        response = query_ollama(
            prompt,
            max_tokens=max_tokens,
            temperature=temperature
        )
        
        if not response or len(response.strip()) < 10:
            print("❌ Empty or invalid response from LLM")
            return "⚠️ Tiada respons yang sah daripada model. Sila cuba lagi."
        
        print(f"✅ Generated response ({len(response)} characters)")
        print("=" * 60)
        
        return response.strip()
        
    except Exception as e:
        print(f"❌ Ollama error: {e}")
        return "⚠️ Ralat semasa menjana respons. Sila cuba lagi atau hubungi pentadbir sistem."


def generate_answer_with_sources(query: str) -> Dict[str, any]:
    """
    Generate answer with source attribution
    
    Returns:
        Dictionary with 'answer', 'sources', and 'metadata'
    """
    embedder = EmbeddingModel()
    chroma = ChromaClient()

    # Detect intent
    level = detect_program_level(query)
    program_name = detect_program_name(query)
    qual_type = detect_qualification_type(query)
    program_code = extract_program_code_from_query(query)

    # Check if comparison query
    comparison_keywords = ['perbezaan', 'beza', 'difference', 'compare', 'berbanding']
    is_comparison = any(kw in query.lower() for kw in comparison_keywords)

    # Build query
    query_parts = [query]
    
    if not is_comparison and level != "Unspecified":
        query_parts.append(level)
    
    if program_name != "Unknown":
        base_name = program_name.replace("Diploma ", "").replace("Degree ", "").strip()
        query_parts.append(base_name)
    
    enhanced_query = " ".join(query_parts)
    query_embed = embedder.encode([enhanced_query])[0]

    # Build filter
    if is_comparison:
        where_filter = build_smart_filter("Unspecified", program_name, None, program_code)
    else:
        where_filter = build_smart_filter(level, program_name, qual_type, program_code)

    # Retrieve
    try:
        results = chroma.query(
            query_embedding=query_embed,
            n_results=10,
            where=where_filter
        )
    except Exception as e:
        print(f"Query with filter failed: {e}, retrying without filter")
        try:
            results = chroma.query(
                query_embedding=query_embed,
                n_results=15
            )
        except:
            results = None

    if not results or not results.get("documents") or not results["documents"][0]:
        return {
            "answer": "⚠️ Tiada maklumat relevan dijumpai.",
            "sources": [],
            "metadata": {
                "level": level,
                "program": program_name,
                "qualification": qual_type,
                "program_code": program_code
            }
        }

    # Process results
    raw_docs = results["documents"][0]
    raw_metadatas = results.get("metadatas", [[]])[0]
    raw_distances = results.get("distances", [[]])[0] if results.get("distances") else []
    
    # For comparison queries, ensure both levels
    if is_comparison:
        diploma_docs = [(d, m, i) for i, (d, m) in enumerate(zip(raw_docs, raw_metadatas)) if m.get('program_level') == 'Diploma']
        degree_docs = [(d, m, i) for i, (d, m) in enumerate(zip(raw_docs, raw_metadatas)) if m.get('program_level') == 'Degree']
        
        selected = diploma_docs[:3] + degree_docs[:3]
        raw_docs = [d for d, m, i in selected]
        raw_metadatas = [m for d, m, i in selected]
        raw_distances = [raw_distances[i] for d, m, i in selected if i < len(raw_distances)]
    else:
        # Prioritize generic programs if needed
        if program_name not in ["Unknown", "Unspecified"]:
            raw_docs, raw_metadatas = prioritize_generic_programs(
                raw_docs, raw_metadatas, query, program_name
            )
    
    unique_docs = deduplicate_documents(raw_docs, threshold=0.85)
    
    # Get corresponding metadata after reordering
    unique_metadatas = []
    unique_distances = []
    for doc in unique_docs:
        try:
            idx = raw_docs.index(doc)
            if idx < len(raw_metadatas):
                unique_metadatas.append(raw_metadatas[idx])
                if idx < len(raw_distances):
                    unique_distances.append(raw_distances[idx])
                else:
                    unique_distances.append(1.0)
            else:
                unique_metadatas.append({})
                unique_distances.append(1.0)
        except ValueError:
            unique_metadatas.append({})
            unique_distances.append(1.0)
    
    # Format context
    num_docs = 8 if is_comparison else 5
    context = format_context(unique_docs[:num_docs], unique_metadatas[:num_docs])

    # Generate answer with appropriate prompt
    if is_comparison:
        prompt = f"""Anda adalah Pegawai Akademik UiTM yang membantu bakal pelajar membandingkan program.

Berdasarkan maklumat rasmi dari dokumen UiTM di bawah, jawab soalan pelajar dengan lengkap dan tepat dalam Bahasa Malaysia yang formal.

=== MAKLUMAT RASMI UiTM ===
{context}

=== SOALAN PELAJAR ===
{query}

=== ARAHAN PENTING ===
1. Gunakan HANYA maklumat dari konteks di atas
2. BANDINGKAN kedua-dua program dengan jelas
3. Sertakan kod program yang BETUL dari konteks
4. Gunakan format berstruktur
5. Nyatakan CGPA dan MUET dengan jelas
6. Fokus pada perbezaan utama

PENTING: Kod program mesti tepat dengan konteks!

Jawapan anda:"""
    else:
        prompt = f"""Anda adalah Pegawai Akademik UiTM yang membantu bakal pelajar.

Berdasarkan maklumat rasmi dari dokumen UiTM di bawah, jawab soalan pelajar dengan lengkap dan tepat dalam Bahasa Malaysia yang formal.

=== MAKLUMAT RASMI UiTM ===
{context}

=== SOALAN PELAJAR ===
{query}

=== ARAHAN PENTING ===
1. Gunakan HANYA maklumat dari konteks di atas
2. Senaraikan SEMUA syarat kelayakan yang relevan
3. Gunakan format berstruktur dengan bullet points
4. Sertakan kod program jika relevan - pastikan kod yang betul dari konteks
5. Nyatakan CGPA dan MUET dengan jelas
6. Gunakan Bahasa Malaysia formal
7. Jika ada beberapa program serupa, bezakan dengan kod program

PENTING: Kod program mesti tepat dengan konteks!

Jawapan anda:"""

    try:
        response = query_ollama(prompt, max_tokens=2048, temperature=0.3)
    except Exception as e:
        response = f"⚠️ Ralat: {str(e)}"

    # Build sources
    sources = []
    for i, (doc, meta) in enumerate(zip(unique_docs[:num_docs], unique_metadatas[:num_docs])):
        source = {
            "rank": i + 1,
            "program_name": meta.get("program_name", "Unknown"),
            "program_code": meta.get("program_code_uitm", "Unknown"),
            "program_level": meta.get("program_level", "Unknown"),
            "source_file": meta.get("source", "Unknown"),
            "chunk_type": meta.get("chunk_type", "Unknown"),
            "similarity": 1 - unique_distances[i] if i < len(unique_distances) else 0,
            "excerpt": doc[:200] + "..." if len(doc) > 200 else doc
        }
        sources.append(source)

    return {
        "answer": response.strip(),
        "sources": sources,
        "metadata": {
            "level": level,
            "program": program_name,
            "qualification": qual_type,
            "program_code": program_code,
            "is_comparison": is_comparison,
            "num_sources": len(sources)
        }
    }


def batch_generate_answers(queries: List[str]) -> List[Dict[str, any]]:
    """
    Generate answers for multiple queries (useful for testing)
    
    Args:
        queries: List of query strings
    
    Returns:
        List of response dictionaries
    """
    results = []
    for i, query in enumerate(queries, 1):
        print(f"\n{'='*60}")
        print(f"Query {i}/{len(queries)}: {query}")
        print(f"{'='*60}")
        
        result = generate_answer_with_sources(query)
        results.append({
            "query": query,
            **result
        })
    
    return results


# =============================================================
# 🧪 Testing Functions
# =============================================================
def test_rag_system():
    """Test the RAG system with sample queries"""
    
    test_queries = [
        "Apakah syarat untuk masuk Diploma Sains Komputer?",
        "Berapa CGPA minimum untuk degree kejuruteraan awam lepasan diploma?",
        "Saya ada SPM dengan 5 kepujian, boleh masuk program apa?",
        "Syarat MUET untuk undang-undang?",
        "Apa beza antara Diploma Sains Komputer dan Diploma Statistik?",
        "Apakah perbezaan Diploma Sains Komputer dan Sarjana Muda Sains Komputer?",
        "Syarat untuk program CDCS230?",
    ]
    
    print("\n" + "="*80)
    print("🧪 TESTING RAG SYSTEM")
    print("="*80)
    
    results = batch_generate_answers(test_queries)
    
    for i, result in enumerate(results, 1):
        print(f"\n{'='*80}")
        print(f"TEST {i}")
        print(f"{'='*80}")
        print(f"Query: {result['query']}")
        print(f"\nAnswer:\n{result['answer']}")
        print(f"\nMetadata: {result['metadata']}")
        print(f"Number of sources: {len(result['sources'])}")
        print(f"\nTop 3 Sources:")
        for source in result['sources'][:3]:
            print(f"  {source['rank']}. {source['program_name']} ({source['program_code']}) - {source['program_level']} - {source['similarity']:.2%}")


# =============================================================
# ▶️ CLI Entry
# =============================================================
if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1:
        # Query from command line
        query = " ".join(sys.argv[1:])
        result = generate_answer_with_sources(query)
        
        print("\n" + "="*80)
        print("JAWAPAN")
        print("="*80)
        print(result['answer'])
        
        print("\n" + "="*80)
        print("SUMBER")
        print("="*80)
        for source in result['sources']:
            print(f"• [{source['rank']}] {source['program_name']} ({source['program_code']}) - {source['program_level']}")
            print(f"  Similarity: {source['similarity']:.2%}")
            print(f"  Excerpt: {source['excerpt']}\n")
        
        print("\n" + "="*80)
        print("METADATA")
        print("="*80)
        print(f"Level: {result['metadata']['level']}")
        print(f"Program: {result['metadata']['program']}")
        print(f"Qualification: {result['metadata']['qualification']}")
        print(f"Program Code: {result['metadata'].get('program_code', 'N/A')}")
        print(f"Is Comparison: {result['metadata'].get('is_comparison', False)}")
    else:
        # Run tests
        test_rag_system()