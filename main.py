"""Main entry point for the application."""
import uvicorn
from app.api import app as fastapi_app
from app.kb_loader import index_knowledge_base

#
# Expose `app` at module level so `uvicorn main:app ...` works.
#
app = fastapi_app

if __name__ == "__main__":
    # Index knowledge base on startup
    print("Initializing knowledge base...")
    index_knowledge_base()
    
    # Run FastAPI app
    uvicorn.run(app, host="0.0.0.0", port=8000)
