import os
import re
import shutil
import uuid
from pathlib import Path
from typing import List, Tuple, Dict, Optional
from dataclasses import dataclass

import pymupdf4llm  # ✅ PDF parser
from app.core.embedding_model import EmbeddingModel
from app.core.chroma_client import ChromaClient
from app.core.config import CHROMA_DIR, CHROMA_DIR_STR


# =============================================================
# 📋 Data Model
# =============================================================
@dataclass
class ProgramInfo:
    program_name: str
    program_code_uitm: str
    program_code_upu: str
    duration: str
    program_level: str
    faculty: str
    requirements_spm: List[str]
    requirements_diploma: List[str]
    requirements_stpm: List[str]
    requirements_asasi: List[str]
    requirements_certificate: List[str]
    requirements_pra_diploma: List[str]
    requirements_apel: List[str]
    requirements_stam: List[str]
    cgpa_requirements: Dict[str, str]
    muet_requirements: str
    eligibility: List[str]
    notes: List[str]
    raw_text: str


# =============================================================
# 🎯 Program Extraction (Enhanced for Malaysian Unis)
# =============================================================
class ProgramExtractor:
    def __init__(self):
        self.program_patterns = {
            "name": r"(Diploma|Sarjana Muda|Ijazah Sarjana Muda|Degree|Bachelor)\s+([^|/\n]+(?:Kepujian|kepujian)?)",
            "code_uitm": r"\b([A-Z]{2,4}\d{3,4})\b",
            "code_upu": r"\b(UE\d{7})\b",
            "duration": r"(\d+\s*½?\s*[Tt]ahun\s*/\s*\d+\s*[Ss]emester)",
            "faculty": r"(KOLEJ PENGAJIAN [A-Z\s&]+|FAKULTI [A-Z\s\-]+)",
            "muet": r"(Band\s*\d+)",
            "cgpa": r"(\d+\.\d+)\s*/\s*Band\s*\d+",
        }

    def extract_program_blocks(self, text: str) -> List[str]:
        """Split document into program blocks"""
        patterns = [
            r"(?=Diploma\s+[A-Z])",
            r"(?=Sarjana Muda\s+[A-Z])",
            r"(?=Bachelor\s+)",
            r"(?=Ijazah\s+)"
        ]
        
        split_pattern = "|".join(patterns)
        blocks = re.split(split_pattern, text)
        
        valid_blocks = [b.strip() for b in blocks if len(b.strip()) > 200]
        
        return valid_blocks

    def extract_requirements(self, text: str, section_name: str) -> List[str]:
        """Extract full requirement blocks for a given qualification type."""
        section_variations = {
            "SPM": r"LEPASAN SPM(?:/SETARAF)?",
            "DIPLOMA_UITM": r"LEPASAN DIPLOMA UiTM",
            "DIPLOMA_IPT": r"LEPASAN DIPLOMA INSTITUSI PENGAJIAN TINGGI",
            "STPM": r"LEPASAN STPM(?:/SETARAF)?",
            "ASASI": r"LEPASAN ASASI UiTM|LEPASAN ASASI SAINS UM|LEPASAN.*MATRIKULASI KPM",
            "SIJIL": r"LEPASAN SIJIL(?:\s+POLITEKNIK)?",
            "PRA_DIPLOMA": r"LEPASAN PRA DIPLOMA",
            "APEL": r"APEL\s*\(ACCREDITATION OF PRIOR EXPERIENTIAL LEARNING\)",
            "STAM": r"LEPASAN STAM",
            "DVM": r"LEPASAN DIPLOMA VOKASIONAL MALAYSIA",
            "DKM": r"LEPASAN DIPLOMA KEMAHIRAN MALAYSIA",
        }
        
        pattern = section_variations.get(section_name, section_name)
        
        regex = rf"{pattern}[:\s]*(.*?)(?=(?:\n[A-Z ]{{5,}}:)|(?=\n?KOLEJ PENGAJIAN)|(?=\n?FAKULTI)|(?=\Z))"
        match = re.search(regex, text, re.DOTALL | re.IGNORECASE)
        
        if not match:
            return []
        
        section_text = match.group(1)
        
        lines = []
        for line in section_text.split("\n"):
            cleaned = re.sub(r"^[•●■▪\-\*◦]+\s*", "", line.strip())
            cleaned = re.sub(r"\s+", " ", cleaned)
            
            if len(cleaned) > 10 and not re.match(r"^\d+\s*/\s*Band", cleaned):
                lines.append(cleaned)
        
        return lines[:50]

    def extract_cgpa_requirements(self, text: str) -> Dict[str, str]:
        """Extract CGPA requirements for different qualifications"""
        cgpa_dict = {}
        
        patterns = {
            "diploma_uitm": r"LEPASAN DIPLOMA UiTM[:\s]*(\d+\.\d+)\s*/\s*Band\s*\d+",
            "diploma_ipt": r"LEPASAN DIPLOMA.*IPT[:\s]*(\d+\.\d+)\s*/\s*Band\s*\d+",
            "stpm": r"LEPASAN STPM[:\s]*(\d+\.\d+)\s*/\s*Band\s*\d+",
            "asasi": r"LEPASAN.*ASASI[:\s]*(\d+\.\d+)\s*/\s*Band\s*\d+",
        }
        
        for key, pattern in patterns.items():
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                cgpa_dict[key] = match.group(1)
        
        return cgpa_dict

    def extract_muet_requirement(self, text: str) -> str:
        """Extract MUET Band requirement"""
        match = re.search(r"Malaysian University English Test[:\s]*\(MUET\)[:\s]*(Band\s*\d+)", text, re.IGNORECASE)
        if match:
            return match.group(1)
        
        match = re.search(r"Band\s*\d+", text)
        return match.group(0) if match else "Band 1"

    def detect_program_level(self, name: str, text: str) -> str:
        """Detect if program is Diploma or Degree"""
        name_lower = name.lower()
        text_lower = text.lower()
        
        if "diploma" in name_lower and "pra diploma" not in name_lower:
            return "Diploma"
        elif any(k in name_lower for k in ["sarjana muda", "ijazah", "degree", "bachelor"]):
            return "Degree"
        elif any(k in text_lower for k in ["4 tahun", "8 semester"]):
            return "Degree"
        elif any(k in text_lower for k in ["2 ½ tahun", "5 semester", "3 tahun", "6 semester"]):
            return "Diploma"
        
        return "Unknown"
    
    def extract_program_name_smart(self, block: str, code_uitm: str) -> str:
        """
        Extract program name intelligently using the program code as anchor
        This handles cases like:
        - "Sarjana Muda Sains Komputer (Kepujian) CDCS230" → "Sarjana Muda Sains Komputer"
        - "Sarjana Muda Sains Komputer (Kepujian) Rangkaian Komputer CDCS255" → "Sarjana Muda Sains Komputer Rangkaian Komputer"
        """
        # Find where the code appears
        code_pos = block.find(code_uitm)
        if code_pos == -1:
            return "Unknown"
        
        # Extract text before the code
        text_before_code = block[:code_pos].strip()
        
        # Take the last line before the code
        lines_before_code = text_before_code.split('\n')
        last_line = lines_before_code[-1].strip() if lines_before_code else ""
        
        # If last line is too short, try previous lines
        if len(last_line) < 20 and len(lines_before_code) > 1:
            last_line = ' '.join(lines_before_code[-2:]).strip()
        
        program_name = last_line
        
        # Remove common prefixes
        prefixes_to_remove = ['Program:', 'Programme:', 'PROGRAM:', 'PROGRAMME:']
        for prefix in prefixes_to_remove:
            if program_name.startswith(prefix):
                program_name = program_name[len(prefix):].strip()
        
        # Remove trailing code if it appears
        program_name = program_name.replace(code_uitm, '').strip()
        
        # Remove UPU code pattern if exists
        program_name = re.sub(r'\s*UE\d{7}\s*', '', program_name)
        
        # Remove (Kepujian) / (Honours)
        program_name = re.sub(r'\s*\(\s*Kepujian\s*\)\s*', ' ', program_name, flags=re.IGNORECASE)
        program_name = re.sub(r'\s*\(\s*Honours?\s*\)\s*', ' ', program_name, flags=re.IGNORECASE)
        
        # Clean up whitespace
        program_name = re.sub(r'\s+', ' ', program_name).strip()
        
        # Standardize level names
        replacements = {
            "Ijazah Sarjana Muda": "Sarjana Muda",
            "Bachelor of": "Sarjana Muda",
            "Degree in": "Sarjana Muda"
        }
        
        for old, new in replacements.items():
            if program_name.startswith(old):
                program_name = program_name.replace(old, new, 1)
                program_name = re.sub(r'\s+', ' ', program_name).strip()
                break
        
        # Final validation
        if len(program_name) < 10 or len(program_name) > 150:
            # Fallback pattern
            match = re.search(
                r'(Diploma|Sarjana Muda|Ijazah Sarjana Muda|Bachelor|Degree)\s+(.+?)(?:\s+' + re.escape(code_uitm) + ')',
                text_before_code,
                re.IGNORECASE
            )
            if match:
                level = match.group(1)
                subject = match.group(2).strip()
                subject = re.sub(r'\s*\(\s*Kepujian\s*\)\s*', '', subject, flags=re.IGNORECASE)
                subject = re.sub(r'\s+', ' ', subject).strip()
                program_name = f"{level} {subject}"
        
        return program_name.strip()
    
    def normalize_program_name(self, name: str, code: str = None) -> str:
        """
        Normalize program name for consistent storage and retrieval
        """
        # Remove extra whitespace
        name = re.sub(r"\s+", " ", name.strip())
        
        # Check if this is a specialized program based on keywords
        specialization_keywords = [
            'Rangkaian Komputer', 'Rangkaian', 'Multimedia', 'Grafik', 'Digital Media',
            'Forensik', 'Keselamatan', 'Web', 'Mobile', 'Game',
            'Artificial Intelligence', 'Machine Learning', 'Data Science',
            'Cloud Computing', 'Cyber', 'Embedded', 'Robotik',
            'Awam', 'Mekanikal', 'Elektrik', 'Kimia', 'Petroleum',
            'Korporat', 'Antarabangsa', 'Syariah', 'Perbankan Islam'
        ]
        
        is_specialized = any(keyword.lower() in name.lower() for keyword in specialization_keywords)
        
        # If specialized, keep full name
        if is_specialized:
            return name.strip(" ,-/")
        
        # For base programs, clean up
        name = name.strip(" ,-/")
        
        return name

    def parse_program(self, block: str) -> Optional[ProgramInfo]:
        """Parse a program block into structured data"""
        try:
            # Extract program code FIRST
            code_uitm_match = re.search(self.program_patterns["code_uitm"], block)
            code_uitm = code_uitm_match.group(1) if code_uitm_match else "Unknown"

            code_upu_match = re.search(self.program_patterns["code_upu"], block)
            code_upu = code_upu_match.group(1) if code_upu_match else "Unknown"

            # Skip if no valid code found
            if code_uitm == "Unknown" and code_upu == "Unknown":
                return None
            
            # Extract program name using smart extraction
            program_name = self.extract_program_name_smart(block, code_uitm)
            
            if not program_name or program_name == "Unknown":
                return None
            
            # Normalize the extracted name
            program_name = self.normalize_program_name(program_name, code_uitm)

            # Extract duration
            duration_match = re.search(self.program_patterns["duration"], block, re.IGNORECASE)
            duration = duration_match.group(1) if duration_match else "Unknown"

            # Extract faculty
            faculty_match = re.search(self.program_patterns["faculty"], block, re.IGNORECASE)
            faculty = faculty_match.group(1).strip() if faculty_match else "Unknown"

            # Detect level
            level = self.detect_program_level(program_name, block)

            # Extract requirements for all categories
            req_spm = self.extract_requirements(block, "SPM")
            req_diploma_uitm = self.extract_requirements(block, "DIPLOMA_UITM")
            req_diploma_ipt = self.extract_requirements(block, "DIPLOMA_IPT")
            req_diploma = req_diploma_uitm + req_diploma_ipt
            req_stpm = self.extract_requirements(block, "STPM")
            req_asasi = self.extract_requirements(block, "ASASI")
            req_cert = self.extract_requirements(block, "SIJIL")
            req_pra = self.extract_requirements(block, "PRA_DIPLOMA")
            req_apel = self.extract_requirements(block, "APEL")
            req_stam = self.extract_requirements(block, "STAM")

            # Extract CGPA and MUET
            cgpa_reqs = self.extract_cgpa_requirements(block)
            muet_req = self.extract_muet_requirement(block)

            # Extract eligibility
            eligibility = []
            elig_match = re.search(
                r"Terbuka kepada[:\s]*(.*?)(?=Syarat Am|Diploma|Sarjana|$)", 
                block, 
                re.DOTALL | re.IGNORECASE
            )
            if elig_match:
                elig_text = elig_match.group(1).strip()
                eligibility = [line.strip() for line in elig_text.split("\n") if len(line.strip()) > 5]

            # Extract notes
            notes = []
            for note_match in re.finditer(
                r"(\d+\.\s+Calon.*?)(?=\d+\.\s+Calon|LEPASAN|$)", 
                block, 
                re.DOTALL
            ):
                note = note_match.group(1).strip()
                if len(note) > 10:
                    notes.append(note[:300])

            return ProgramInfo(
                program_name=program_name,
                program_code_uitm=code_uitm,
                program_code_upu=code_upu,
                duration=duration,
                program_level=level,
                faculty=faculty,
                requirements_spm=req_spm,
                requirements_diploma=req_diploma,
                requirements_stpm=req_stpm,
                requirements_asasi=req_asasi,
                requirements_certificate=req_cert,
                requirements_pra_diploma=req_pra,
                requirements_apel=req_apel,
                requirements_stam=req_stam,
                cgpa_requirements=cgpa_reqs,
                muet_requirements=muet_req,
                eligibility=eligibility,
                notes=notes,
                raw_text=block[:800],
            )
        except Exception as e:
            print(f"⚠️ Failed to parse block: {e}")
            return None


# =============================================================
# 📄 PDF Extraction & Chunking
# =============================================================
def extract_and_chunk_structured(path: str) -> List[Tuple[str, Dict]]:
    """Extract and chunk PDF into structured pieces"""
    try:
        markdown_text = pymupdf4llm.to_markdown(path)
        print(f"✅ Extracted {len(markdown_text)} characters from PDF")
    except Exception as e:
        print(f"❌ Failed to extract from {path}: {e}")
        return []

    extractor = ProgramExtractor()
    blocks = extractor.extract_program_blocks(markdown_text)
    print(f"📦 Found {len(blocks)} program blocks")

    chunks = []
    programs_found = 0
    
    for block in blocks:
        program = extractor.parse_program(block)
        if not program or program.program_code_uitm == "Unknown":
            continue

        programs_found += 1
        
        # Determine if specialized
        is_specialized = any(kw.lower() in program.program_name.lower() 
                            for kw in ['rangkaian', 'multimedia', 'grafik', 'forensik', 
                                      'keselamatan', 'web', 'mobile', 'game', 'data'])
        
        specialization_marker = "🔸 SPECIALIZED" if is_specialized else "⭐ BASE"
        print(f"  ✓ {specialization_marker} | {program.program_name} ({program.program_code_uitm}) - {program.program_level}")

        # Base metadata for all chunks
        base_metadata = {
            "source": os.path.basename(path),
            "program_name": program.program_name,
            "program_code_uitm": program.program_code_uitm,
            "program_code_upu": program.program_code_upu,
            "program_level": program.program_level,
            "duration": program.duration,
            "faculty": program.faculty,
        }

        # 1️⃣ Overview Chunk
        overview_text = f"""Program: {program.program_name}
Kod UiTM: {program.program_code_uitm}
Kod UPU: {program.program_code_upu}
Tahap: {program.program_level}
Tempoh: {program.duration}
Fakulti: {program.faculty}
Keperluan MUET: {program.muet_requirements}

Kelayakan: {' | '.join(program.eligibility) if program.eligibility else 'Terbuka kepada keturunan Melayu, Anak Negeri Sabah, Anak Negeri Sarawak dan Orang Asli'}
"""
        
        if program.notes:
            overview_text += f"\n\nNota Penting:\n" + "\n".join(f"• {note}" for note in program.notes[:3])

        chunks.append((overview_text, {**base_metadata, "chunk_type": "overview"}))

        # 2️⃣ Requirements Chunks
        requirement_sections = [
            ("SPM", program.requirements_spm, "Syarat Lepasan SPM"),
            ("Diploma", program.requirements_diploma, "Syarat Lepasan Diploma"),
            ("STPM", program.requirements_stpm, "Syarat Lepasan STPM"),
            ("Asasi/Matrikulasi", program.requirements_asasi, "Syarat Lepasan Asasi/Matrikulasi"),
            ("Sijil", program.requirements_certificate, "Syarat Lepasan Sijil"),
            ("Pra Diploma", program.requirements_pra_diploma, "Syarat Lepasan Pra Diploma"),
            ("APEL", program.requirements_apel, "Syarat APEL"),
            ("STAM", program.requirements_stam, "Syarat Lepasan STAM"),
        ]

        for section_key, items, section_title in requirement_sections:
            if not items:
                continue

            cgpa_info = ""
            if section_key == "Diploma" and "diploma_uitm" in program.cgpa_requirements:
                cgpa_info = f"\nMinimum CGPA: {program.cgpa_requirements['diploma_uitm']}"
            elif section_key == "STPM" and "stpm" in program.cgpa_requirements:
                cgpa_info = f"\nMinimum CGPA/PNGK: {program.cgpa_requirements['stpm']}"

            req_text = f"""{section_title} untuk {program.program_name} ({program.program_code_uitm}):
{cgpa_info}
MUET: {program.muet_requirements}

Syarat:
{chr(10).join('• ' + item for item in items[:10])}
"""
            
            chunks.append((
                req_text,
                {
                    **base_metadata,
                    "chunk_type": f"requirements_{section_key.lower().replace('/', '_')}",
                    "requirement_type": section_key,
                }
            ))

    print(f"✅ Extracted {programs_found} programs → {len(chunks)} chunks")
    return chunks


# =============================================================
# 🗑️ Reset ChromaDB safely
# =============================================================
def reset_chromadb():
    """Reset ChromaDB by removing and recreating directory"""
    chroma_path = Path(CHROMA_DIR_STR).resolve()
    print(f"🧭 ChromaDB path: {chroma_path}")
    
    try:
        if chroma_path.exists():
            print(f"🗑️ Removing old ChromaDB at: {chroma_path}")
            shutil.rmtree(chroma_path, ignore_errors=True)
    except Exception as e:
        print(f"⚠️ Could not remove ChromaDB: {e}")
    
    chroma_path.mkdir(parents=True, exist_ok=True)
    print(f"📁 Created new ChromaDB directory at: {chroma_path}")


# =============================================================
# 🚀 Ingest PDFs
# =============================================================
def ingest_documents(data_dir: str = "data"):
    """Main ingestion pipeline"""
    print("=" * 60)
    print("🚀 Starting Document Ingestion Pipeline")
    print("=" * 60)
    
    embedder = EmbeddingModel()
    chroma = ChromaClient()

    reset_chromadb()

    data_path = Path(data_dir).resolve()
    pdf_files = list(data_path.rglob("*.pdf"))
    
    if not pdf_files:
        print(f"❌ No PDF files found in {data_path}")
        return
    
    print(f"📚 Found {len(pdf_files)} PDF files in {data_path}\n")

    total_chunks = 0
    
    for idx, pdf_file in enumerate(pdf_files, 1):
        print(f"\n{'=' * 60}")
        print(f"📄 [{idx}/{len(pdf_files)}] Processing: {pdf_file.name}")
        print(f"{'=' * 60}")
        
        chunks = extract_and_chunk_structured(str(pdf_file))
        
        if not chunks:
            print(f"⚠️ No chunks extracted from {pdf_file.name}")
            continue

        texts = [t for t, _ in chunks]
        metadatas = [m for _, m in chunks]
        ids = [str(uuid.uuid4()) for _ in chunks]

        print(f"🔄 Generating embeddings for {len(texts)} chunks...")
        try:
            embeddings = embedder.encode(texts)
        except Exception as e:
            print(f"❌ Failed to generate embeddings: {e}")
            continue

        print(f"💾 Adding to ChromaDB...")
        try:
            chroma.add_documents(
                documents=texts,
                embeddings=embeddings,
                metadatas=metadatas,
                ids=ids,
            )
            total_chunks += len(chunks)
            print(f"✅ Successfully added {len(chunks)} chunks from {pdf_file.name}")
        except Exception as e:
            print(f"❌ Failed to add to ChromaDB: {e}")

    print("\n" + "=" * 60)
    print(f"🎉 Ingestion Complete!")
    print(f"📊 Total chunks processed: {total_chunks}")
    print(f"📁 Database location: {CHROMA_DIR}")
    print("=" * 60)


# =============================================================
# 🔍 Query Helper Functions
# =============================================================
def detect_program_level(query: str) -> str:
    """Detect if query is about Diploma or Degree"""
    query_lower = query.lower()
    
    if any(w in query_lower for w in ["diploma"]) and "pra" not in query_lower:
        return "Diploma"
    elif any(w in query_lower for w in ["degree", "ijazah", "sarjana muda", "bachelor"]):
        return "Degree"
    
    degree_subjects = ["undang", "law", "legal", "kejuruteraan", "engineering"]
    if any(w in query_lower for w in degree_subjects):
        return "Degree"
    
    return "Unspecified"


def detect_program_name(query: str) -> str:
    """Detect program name from query"""
    programs = {
        r"sains komputer|computer science|cs\b|komputer": "Sains Komputer",
        r"teknologi maklumat|information technology|it\b": "Teknologi Maklumat",
        r"sistem maklumat|information system": "Sistem Maklumat",
        r"rangkaian|network|networking": "Rangkaian Komputer",
        r"multimedia|multimedia computing": "Multimedia",
        r"keselamatan|security|cyber": "Keselamatan Siber",
        r"statistik|statistics": "Statistik",
        r"aktuari|actuarial": "Sains Aktuari",
        r"sains matematik|mathematical science|matematik": "Sains Matematik",
        r"pengurusan maklumat|information management": "Pengurusan Maklumat",
        r"perpustakaan|library": "Perpustakaan",
        r"rekod|records": "Pengurusan Rekod",
        r"kejuruteraan awam|civil engineering|awam": "Kejuruteraan Awam",
        r"infrastruktur|infrastructure": "Infrastruktur",
        r"pembinaan|construction": "Pembinaan",
        r"kejuruteraan mekanikal|mechanical engineering|mekanikal": "Kejuruteraan Mekanikal",
        r"mekatronik|mechatronic": "Mekatronik",
        r"pembuatan|manufacturing": "Pembuatan",
        r"kejuruteraan elektrik|electrical engineering|elektrik": "Kejuruteraan Elektrik",
        r"elektronik|electronic": "Elektronik",
        r"kuasa|power": "Kuasa Elektrik",
        r"kejuruteraan kimia|chemical engineering|kimia": "Kejuruteraan Kimia",
        r"minyak dan gas|oil and gas": "Minyak dan Gas",
        r"undang|law|legal": "Undang-Undang",
        r"perniagaan|business": "Perniagaan",
        r"perakaunan|accounting": "Perakaunan",
    }
    
    query_lower = query.lower()
    for pattern, name in programs.items():
        if re.search(pattern, query_lower):
            return name
    
    return "Unknown"


def detect_qualification_type(query: str) -> Optional[str]:
    """Detect what qualification the user is asking about"""
    query_lower = query.lower()
    
    qualifications = {
        "spm": ["spm", "sijil pelajaran malaysia"],
        "diploma": ["diploma", "dip"],
        "stpm": ["stpm", "sijil tinggi"],
        "asasi": ["asasi", "matrikulasi", "foundation"],
        "apel": ["apel", "prior learning"],
        "stam": ["stam", "sijil tinggi agama"],
    }
    
    for qual_type, keywords in qualifications.items():
        if any(kw in query_lower for kw in keywords):
            return qual_type
    
    return None


# =============================================================
# ▶️ CLI Entry
# =============================================================
if __name__ == "__main__":
    ingest_documents("data")