"""Knowledge base search tool."""
from typing import List
from app.vector_store import vector_store
from app.llm_client import llm_client
from app.agent.models import KBResult


def search_knowledge_base(query: str, top_k: int = 3) -> List[KBResult]:
    """
    Search the knowledge base using RAG (embedding)
    """
    # Embed the query
    query_embedding = llm_client.embed_text(query)
    
    # Search vector store
    results = vector_store.query(
        query_embedding=query_embedding,
        n_results=top_k,
    )
    
    # Convert to KBResult objects
    kb_results = []
    if results["ids"] and len(results["ids"][0]) > 0:
        ids = results["ids"][0]
        documents = results["documents"][0]
        metadatas = results["metadatas"][0]
        distances = results["distances"][0]
        
        for i in range(len(ids)):
            # Convert distance to similarity score 
            score = 1.0 - distances[i] if distances[i] <= 1.0 else 0.0
            
            kb_results.append(KBResult(
                id=ids[i],
                title=metadatas[i].get("title", "Untitled"),
                snippet=documents[i][:500],  # Limit snippet length
                score=score,
            ))
    
    return kb_results
