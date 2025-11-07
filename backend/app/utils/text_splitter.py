import re

def chunk_text(text: str, max_length: int = 2000) -> list[str]:
    """
    Chunk UiTM course documents by section headings (e.g., 'Diploma Sains Komputer').
    Keeps full sections intact for accurate retrieval.
    """

    # Normalize whitespace and remove excessive line breaks
    text = re.sub(r'\s+', ' ', text.strip())

    # Split by major UiTM program section markers
    sections = re.split(
        r'(?=(?:Diploma|Sarjana Muda)\s+[A-Za-z/& ]+)', 
        text, 
        flags=re.IGNORECASE
    )

    chunks = []
    for section in sections:
        section = section.strip()
        if not section:
            continue

        # Skip short irrelevant sections
        if len(section) < 100:
            continue

        # If section too long, split into smaller chunks
        if len(section) > max_length:
            for i in range(0, len(section), max_length):
                chunks.append(section[i:i+max_length].strip())
        else:
            chunks.append(section)

    return chunks
