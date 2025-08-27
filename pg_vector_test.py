import asyncio
import os
import uuid
from dotenv import load_dotenv
from langchain_core.documents import Document
from rag_pipeline.src.models.multilingual_embedder import MultilingualEmbedder
from rag_pipeline.config.settings import (
    DEFAULT_EMBEDDING_MODEL, DEFAULT_BATCH_SIZE
)
from AIChatbotService.services.database_service import DatabaseService
from AIChatbotService.database import db_manager

load_dotenv()

async def main():
    # Init DB
    await db_manager.initialize()
    await db_manager.create_tables()

    service = DatabaseService()

    # Init embedder
    multilingual_embedder = MultilingualEmbedder(
        model_name=DEFAULT_EMBEDDING_MODEL,
        batch_size=DEFAULT_BATCH_SIZE
    )

    # Test docs
    test_docs = [
        Document(page_content="This is a test document about machine learning", metadata={"source": "test1"}),
        Document(page_content="Another document discussing artificial intelligence", metadata={"source": "test2"}),
    ]

    # Extract text for embedding
    texts = [doc.page_content for doc in test_docs]

    # Create embeddings
    vectors = multilingual_embedder.embed_documents(texts)

    # Store in DB
    for doc, vector in zip(test_docs, vectors):
        await service.add_embedding(
            content=doc.page_content,
            embedding_vector=vector,
            meta_data=doc.metadata
        )

    print("✅ Embeddings added to database.")

    await db_manager.close()

if __name__ == "__main__":
    asyncio.run(main())
