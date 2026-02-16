"""Knowledge base loader - loads and indexes KB documents into Chroma."""
import json
import os
from pathlib import Path
from typing import List, Dict, Any, Optional
import hashlib

from app.config import settings
from app.vector_store import vector_store
from app.llm_client import llm_client

MANIFEST_FILENAME = "kb_manifest.json"


def chunk_text(text: str, chunk_size: int = 500, overlap: int = 50) -> List[str]:
    """
    Simple text chunking by paragraphs and sentences.
    
    Args:
        text: Text to chunk
        chunk_size: Target chunk size in characters
        overlap: Overlap between chunks
    
    Returns:
        List of text chunks
    """
    # Split by double newlines (paragraphs)
    paragraphs = text.split("\n\n")
    chunks = []
    current_chunk = ""
    
    for para in paragraphs:
        para = para.strip()
        if not para:
            continue
        
        # If adding this paragraph would exceed chunk size, save current chunk
        if current_chunk and len(current_chunk) + len(para) > chunk_size:
            chunks.append(current_chunk.strip())
            # Start new chunk with overlap
            overlap_text = current_chunk[-overlap:] if len(current_chunk) > overlap else current_chunk
            current_chunk = overlap_text + "\n\n" + para
        else:
            if current_chunk:
                current_chunk += "\n\n" + para
            else:
                current_chunk = para
    
    if current_chunk:
        chunks.append(current_chunk.strip())
    
    return chunks


def load_kb_documents() -> List[Dict[str, Any]]:
    """
    Load all KB documents from the KB directory.
    
    Returns:
        List of dicts with 'title', 'content', 'file' keys
    """
    kb_path = Path(settings.kb_path)
    if not kb_path.exists():
        return []
    
    documents = []
    
    # Load markdown files
    for md_file in kb_path.glob("*.md"):
        with open(md_file, "r", encoding="utf-8") as f:
            content = f.read()
        
        # Extract title from first line or filename
        lines = content.split("\n")
        title = lines[0].strip("# ").strip() if lines and lines[0].startswith("#") else md_file.stem
        
        documents.append({
            "title": title,
            "content": content,
            "file": md_file.name,
        })
    
    return documents


def _current_kb_manifest() -> Dict[str, float]:
    """Return a manifest of KB files: {filename: mtime} for each .md in kb_path."""
    kb_path = Path(settings.kb_path)
    if not kb_path.exists():
        return {}
    return {
        f.name: f.stat().st_mtime
        for f in kb_path.glob("*.md")
    }


def _load_manifest() -> Optional[Dict[str, float]]:
    """Load saved manifest from chroma_db dir, or None if missing/invalid."""
    manifest_path = Path(settings.chroma_db_path) / MANIFEST_FILENAME
    if not manifest_path.exists():
        return None
    try:
        with open(manifest_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return None


def _save_manifest(manifest: Dict[str, float]) -> None:
    """Save manifest next to Chroma DB so we know when KB has changed."""
    Path(settings.chroma_db_path).mkdir(parents=True, exist_ok=True)
    manifest_path = Path(settings.chroma_db_path) / MANIFEST_FILENAME
    with open(manifest_path, "w", encoding="utf-8") as f:
        json.dump(manifest, f, sort_keys=True)


def _kb_changed() -> bool:
    """True if KB files were added, removed, or modified since last index."""
    current = _current_kb_manifest()
    saved = _load_manifest()
    if saved is None:
        return True
    return current != saved


def index_knowledge_base(force_reindex: bool = False):
    """
    Load KB documents, chunk them, embed, and index into Chroma.
    Reindex automatically when KB files are added, removed, or modified.
    
    Args:
        force_reindex: If True, clear existing index and reindex
    """
    # Reindex if KB files changed (new, removed, or edited) or if user asked for --force
    if not force_reindex and vector_store.collection.count() > 0 and not _kb_changed():
        print(f"Knowledge base already indexed ({vector_store.collection.count()} documents). Skipping.")
        return
    
    if not force_reindex and vector_store.collection.count() > 0 and _kb_changed():
        print("Knowledge base files changed. Reindexing...")
        force_reindex = True
    
    print("Loading knowledge base documents...")
    documents = load_kb_documents()
    
    if not documents:
        print(f"No KB documents found in {settings.kb_path}")
        return
    
    print(f"Found {len(documents)} KB documents. Chunking and indexing...")
    
    all_chunks = []
    all_metadatas = []
    all_ids = []
    
    for doc in documents:
        chunks = chunk_text(doc["content"])
        
        for i, chunk in enumerate(chunks):
            chunk_id = hashlib.md5(f"{doc['file']}_{i}".encode()).hexdigest()
            all_chunks.append(chunk)
            all_metadatas.append({
                "title": doc["title"],
                "file": doc["file"],
                "chunk_index": i,
            })
            all_ids.append(chunk_id)
    
    print(f"Generated {len(all_chunks)} chunks. Generating embeddings...")
    
    # Generate embeddings in batches
    batch_size = 10
    embeddings = []
    for i in range(0, len(all_chunks), batch_size):
        batch = all_chunks[i:i + batch_size]
        batch_embeddings = [llm_client.embed_text(chunk) for chunk in batch]
        embeddings.extend(batch_embeddings)
        print(f"Embedded {min(i + batch_size, len(all_chunks))}/{len(all_chunks)} chunks...")
    
    # Clear if force reindex
    if force_reindex:
        vector_store.clear()
    
    # Add to vector store
    vector_store.add_documents(
        ids=all_ids,
        texts=all_chunks,
        embeddings=embeddings,
        metadatas=all_metadatas,
    )
    
    _save_manifest(_current_kb_manifest())
    print(f"Indexed {len(all_chunks)} chunks into vector store.")


if __name__ == "__main__":
    # Force reindex (use after adding or editing KB docs in data/kb/)
    import sys
    force = "--force" in sys.argv or "-f" in sys.argv
    index_knowledge_base(force_reindex=force)
