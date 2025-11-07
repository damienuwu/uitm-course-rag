"""
Diagnostic script to check what programs are in ChromaDB
Run this to verify your data after ingestion
"""

from app.core.chroma_client import ChromaClient
from collections import defaultdict

def diagnose_database():
    """Check what programs are stored in ChromaDB"""
    print("\n" + "="*80)
    print("🔍 CHROMADB DIAGNOSTIC REPORT")
    print("="*80)
    
    chroma = ChromaClient()
    
    # Get all documents
    try:
        results = chroma.collection.get(
            limit=1000,  # Adjust if you have more
            include=['metadatas']
        )
    except Exception as e:
        print(f"❌ Error accessing database: {e}")
        return
    
    if not results or not results.get('metadatas'):
        print("❌ No documents found in database!")
        return
    
    metadatas = results['metadatas']
    print(f"\n📊 Total documents in database: {len(metadatas)}")
    
    # Group by program
    programs = defaultdict(lambda: {'count': 0, 'level': '', 'codes': set()})
    
    for meta in metadatas:
        prog_name = meta.get('program_name', 'Unknown')
        prog_code = meta.get('program_code_uitm', 'N/A')
        prog_level = meta.get('program_level', 'Unknown')
        
        programs[prog_name]['count'] += 1
        programs[prog_name]['level'] = prog_level
        programs[prog_name]['codes'].add(prog_code)
    
    print(f"\n📚 Unique programs found: {len(programs)}")
    print("\n" + "="*80)
    print("PROGRAMS LIST")
    print("="*80)
    
    # Sort by name
    sorted_programs = sorted(programs.items(), key=lambda x: (x[1]['level'], x[0]))
    
    current_level = None
    for prog_name, info in sorted_programs:
        level = info['level']
        
        # Print level header
        if level != current_level:
            print(f"\n{'─'*80}")
            print(f"📌 {level.upper()} PROGRAMS")
            print(f"{'─'*80}")
            current_level = level
        
        codes_str = ', '.join(sorted(info['codes']))
        
        # Check if specialized
        is_specialized = any(kw in prog_name.lower() for kw in 
                           ['rangkaian', 'multimedia', 'grafik', 'forensik', 
                            'keselamatan', 'web', 'mobile', 'game', 'data'])
        
        marker = "🔸" if is_specialized else "⭐"
        
        print(f"{marker} {prog_name}")
        print(f"   Codes: {codes_str}")
        print(f"   Chunks: {info['count']}")
        print()
    
    # Check for Sains Komputer specifically
    print("\n" + "="*80)
    print("🔎 SAINS KOMPUTER PROGRAMS DETAILED CHECK")
    print("="*80)
    
    sk_programs = [p for p in sorted_programs if 'sains komputer' in p[0].lower()]
    
    if not sk_programs:
        print("❌ No Sains Komputer programs found!")
    else:
        print(f"✅ Found {len(sk_programs)} Sains Komputer program(s):\n")
        
        for prog_name, info in sk_programs:
            codes = sorted(info['codes'])
            print(f"{'─'*80}")
            print(f"Program: {prog_name}")
            print(f"Level: {info['level']}")
            print(f"Codes: {', '.join(codes)}")
            print(f"Chunks: {info['count']}")
            
            # Get sample chunk
            try:
                sample = chroma.collection.get(
                    where={
                        "$and": [
                            {"program_name": {"$eq": prog_name}},
                            {"chunk_type": {"$eq": "overview"}}
                        ]
                    },
                    limit=1,
                    include=['documents', 'metadatas']
                )
                
                if sample and sample.get('documents'):
                    print(f"\nSample Overview Chunk:")
                    print(f"{'─'*40}")
                    print(sample['documents'][0][:300] + "...")
            except Exception as e:
                print(f"⚠️ Could not retrieve sample: {e}")
            
            print()
    
    # Check for potential issues
    print("\n" + "="*80)
    print("⚠️ POTENTIAL ISSUES")
    print("="*80)
    
    issues_found = False
    
    # Check for duplicate codes
    code_to_programs = defaultdict(list)
    for prog_name, info in programs.items():
        for code in info['codes']:
            if code != 'N/A':
                code_to_programs[code].append(prog_name)
    
    duplicates = {code: progs for code, progs in code_to_programs.items() if len(progs) > 1}
    
    if duplicates:
        issues_found = True
        print("\n⚠️ Programs with same code (potential confusion):")
        for code, progs in duplicates.items():
            print(f"\n   Code {code}:")
            for prog in progs:
                print(f"   - {prog}")
    
    # Check for very similar names
    prog_names = list(programs.keys())
    similar_pairs = []
    
    from difflib import SequenceMatcher
    
    for i, name1 in enumerate(prog_names):
        for name2 in prog_names[i+1:]:
            similarity = SequenceMatcher(None, name1.lower(), name2.lower()).ratio()
            if similarity > 0.85 and name1 != name2:
                similar_pairs.append((name1, name2, similarity))
    
    if similar_pairs:
        issues_found = True
        print("\n⚠️ Very similar program names (might cause confusion):")
        for name1, name2, sim in similar_pairs:
            print(f"\n   Similarity: {sim:.1%}")
            print(f"   - {name1}")
            print(f"   - {name2}")
    
    if not issues_found:
        print("\n✅ No obvious issues detected!")
    
    print("\n" + "="*80)
    print("END OF DIAGNOSTIC REPORT")
    print("="*80)


if __name__ == "__main__":
    diagnose_database()