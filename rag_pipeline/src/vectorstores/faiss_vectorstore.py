from rag_pipeline.src.abstracts.abstract_vector_db import VectorStoreBase
from rag_pipeline.src.models.reranker import Reranker  
import faiss
import numpy as np
from langchain.schema import Document
import pickle 
import os
import logging
from tqdm import tqdm

# Configure logging
logger = logging.getLogger(__name__)

class Fais_VS(VectorStoreBase):
    def __init__(self, embedder_model=None, reranker_model=None):
        """Initialize FAISS vector store with optional reranking capabilities."""
        logger.info("🗄️ Initializing FAISS VectorStore...")
        
        self.index = None
        self.chunks_dict = None
        self.dimension = None
        self.total_vectors = 0
        self.index_type = "IndexFlatIP"
        self.embedder_model = embedder_model
        self.enable_reranking = True
        self.reranker = Reranker()
        # Enhanced functionality attributes
        self.docstore = None
        self.index_to_docstore_id = None
        self.documents = None  # Store original Document objects
        
        if embedder_model:
            logger.info("✅ FAISS VectorStore initialized with embedder model")
        else:
            logger.info("⚠️ FAISS VectorStore initialized without embedder model")
    
    def create_vector_store(self, documents, embedder_model=None):
        """Create FAISS vector store from a list of documents."""
        logger.info(f"🔧 Creating vector store from {len(documents)} documents...")
        
        if embedder_model:
            logger.info("🔄 Updating embedder model...")
            self.embedder_model = embedder_model
        
        if not self.embedder_model:
            logger.error("❌ No embedder model available")
            raise ValueError("Embedder model is required")
        
        # Extract texts
        logger.info("📝 Extracting texts from documents...")
        texts = [doc.page_content for doc in tqdm(documents, desc="📄 Extracting texts", unit="doc")]
        
        # Generate embeddings
        logger.info(f"🧠 Generating embeddings for {len(texts)} texts...")
        with tqdm(total=1, desc="⚡ Creating embeddings", unit="batch") as pbar:
            embeddings = self.embedder_model.batch_embed(texts)
            pbar.update(1)
            
        embeddings = np.array(embeddings).astype("float32")
        logger.info(f"✅ Embeddings generated - Shape: {embeddings.shape}")
        
        # Ensure embeddings are 2D
        if embeddings.ndim == 1:
            logger.debug("🔄 Reshaping 1D embeddings to 2D...")
            embeddings = embeddings.reshape(1, -1)
        
        # Initialize FAISS index
        self.dimension = embeddings.shape[1]
        logger.info(f"🔢 Initializing FAISS IndexFlatIP with dimension {self.dimension}...")
        self.index = faiss.IndexFlatIP(self.dimension)
        
        # Add embeddings to index
        logger.info("📊 Adding embeddings to FAISS index...")
        with tqdm(total=1, desc="💾 Building index", unit="operation") as pbar:
            self.index.add(embeddings)
            pbar.update(1)
        
        # Store text chunks with their indices
        logger.info("🗃️ Creating chunks dictionary...")
        self.chunks_dict = {i: text for i, text in enumerate(tqdm(texts, desc="🔗 Mapping chunks", unit="chunk", leave=False))}
        self.total_vectors = self.index.ntotal
        
        logger.info(f"✅ Vector store created successfully - {self.total_vectors} vectors of dim {self.dimension}")
        print(f"[FAISS] Created index with {self.total_vectors} vectors of dim {self.dimension}")
        return self
    
    def create_vectorstore(self, docs, normalize_embeddings=True):
        """Create enhanced FAISS vector store from Document objects with metadata."""
        logger.info(f"🚀 Creating enhanced vectorstore from {len(docs)} Document objects...")
        logger.info(f"⚙️ Normalization: {'enabled' if normalize_embeddings else 'disabled'}")
        
        if not self.embedder_model:
            logger.error("❌ No embedder model available")
            raise ValueError("Embedder model is required. Set it during initialization or call set_embedder_model()")
        
        # Extract texts from Document objects
        logger.info("📝 Extracting texts from Document objects...")
        texts = [doc.page_content for doc in tqdm(docs, desc="📄 Processing docs", unit="doc")]
        
        # Generate embeddings
        logger.info(f"🧠 Generating embeddings for {len(texts)} documents...")
        with tqdm(total=1, desc="⚡ Creating embeddings", unit="batch") as pbar:
            embeddings = self.embedder_model.batch_embed(texts)
            pbar.update(1)
            
        embeddings = np.array(embeddings).astype("float32")
        logger.info(f"✅ Embeddings generated - Shape: {embeddings.shape}")
        
        # Ensure embeddings are 2D
        if embeddings.ndim == 1:
            logger.debug("🔄 Reshaping 1D embeddings to 2D...")
            embeddings = embeddings.reshape(1, -1)
        
        # Initialize FAISS Index
        self.dimension = embeddings.shape[1]
        logger.info(f"🔢 Initializing FAISS IndexFlatIP with dimension {self.dimension}...")
        self.index = faiss.IndexFlatIP(self.dimension)
        
        # Normalize embeddings for cosine similarity if requested
        if normalize_embeddings:
            logger.info("🎯 Normalizing embeddings for cosine similarity...")
            with tqdm(total=1, desc="🔍 Normalizing", unit="operation") as pbar:
                faiss.normalize_L2(embeddings)
                pbar.update(1)
        
        # Add embeddings to index
        logger.info("📊 Adding embeddings to FAISS index...")
        with tqdm(total=1, desc="💾 Building index", unit="operation") as pbar:
            self.index.add(embeddings)
            pbar.update(1)
        
        # Store enhanced metadata
        logger.info("🗃️ Creating enhanced document storage...")
        self.documents = docs
        
        with tqdm(total=len(docs), desc="🔗 Creating mappings", unit="doc", leave=False) as pbar:
            self.docstore = {str(i): doc for i, doc in enumerate(docs)}
            self.index_to_docstore_id = {i: str(i) for i in range(len(docs))}
            pbar.update(len(docs))
        
        # Maintain backward compatibility
        self.chunks_dict = {i: doc.page_content for i, doc in enumerate(docs)}
        self.total_vectors = self.index.ntotal
        
        logger.info(f"✅ Enhanced vectorstore created successfully!")
        logger.info(f"📊 Statistics: {self.total_vectors} documents, dim {self.dimension}")
        print(f"[FAISS] Created vectorstore with {self.total_vectors} documents of dim {self.dimension}")
        print(f"[FAISS] Normalization: {'enabled' if normalize_embeddings else 'disabled'}")
        
        return self
    
    def get_relevant_documents(self, query, top_k=5):
        """Search and retrieve the most relevant documents for a query with optional reranking."""
        
        # Get query embedding
        logger.debug("🧠 Generating query embedding...")
        with tqdm(total=1, desc="⚡ Embedding query", unit="query", leave=False) as pbar:
            if isinstance(query, str):
                # Use embed_query if available, otherwise fall back to batch_embed
                if hasattr(self.embedder_model, 'embed_query'):
                    query_embedding = self.embedder_model.embed_query(query)
                else:
                    query_embedding = self.embedder_model.batch_embed([query])
                    if isinstance(query_embedding, list) and len(query_embedding) > 0:
                        query_embedding = query_embedding[0]
                    elif isinstance(query_embedding, np.ndarray) and query_embedding.ndim > 1:
                        query_embedding = query_embedding[0]
            else:
                query_embedding = self.embedder_model.batch_embed(query)
            pbar.update(1)
        
        # Initial vector search
        if self.docstore is not None:
            logger.debug("🔍 Using enhanced docstore-based retrieval...")
            candidates = self._search_with_docstore(query_embedding, initial_k=5)
        else:
            logger.debug("🔍 Using chunk-based retrieval...")
            candidates = self._search_chunks(query_embedding, initial_k=5)
            # Convert to Document objects for consistency
            candidates = [
                Document(page_content=res['text'], metadata={"similarity": res['similarity']})
                for res in candidates
            ]

        logger.info(f"🎯 Applying reranking to {len(candidates)} candidates...")
        candidates = self.reranker.rerank_chunks(query, candidates)
            
        # Update metadata 
        for doc in candidates:
            if doc.metadata:
                doc.metadata["reranked"] = True

        # Return top_k results
        results = candidates[:top_k]
        
        rerank_status = "with reranking" 
        logger.info(f"✅ Retrieved {len(results)} relevant documents {rerank_status}")
        
        return results
    def set_embedder_model(self, embedder_model):
        """Set or update the embedder model."""
        logger.info("🔧 Setting embedder model...")
        self.embedder_model = embedder_model
        logger.info("✅ Embedder model updated successfully")
        return self
    
    def _search_with_docstore(self, query_embedding, top_k=5):
        """Search using enhanced docstore and return Document objects."""
        logger.debug(f"🔍 Searching with docstore for top_{top_k} results...")
        
        # Ensure query_embedding is properly shaped
        query_embedding = np.array(query_embedding).astype("float32")
        
        # Handle different input shapes
        if query_embedding.ndim == 1:
            query_embedding = query_embedding.reshape(1, -1)
        elif query_embedding.ndim > 2:
            query_embedding = query_embedding.reshape(1, -1)
        
        # Verify dimensions match
        if query_embedding.shape[1] != self.dimension:
            logger.error(f"❌ Dimension mismatch: query {query_embedding.shape[1]} vs index {self.dimension}")
            raise ValueError(f"Query embedding dimension {query_embedding.shape[1]} doesn't match index dimension {self.dimension}")
        
        # Search FAISS index
        logger.debug("🔎 Executing FAISS search...")
        with tqdm(total=1, desc="🔎 FAISS search", unit="search", leave=False) as pbar:
            distances, indices = self.index.search(query_embedding, top_k)
            pbar.update(1)
        
        # Format results using docstore
        logger.debug("📋 Formatting search results...")
        documents = []
        
        for i in tqdm(range(top_k), desc="📄 Processing results", unit="result", leave=False):
            faiss_idx = indices[0][i]
            if faiss_idx != -1 and faiss_idx in self.index_to_docstore_id:
                docstore_id = self.index_to_docstore_id[faiss_idx]
                if docstore_id in self.docstore:
                    doc = self.docstore[docstore_id]
                    similarity = float(distances[0][i])
                    
                    # Create a copy of the document with updated metadata
                    enhanced_metadata = doc.metadata.copy() if doc.metadata else {}
                    enhanced_metadata["similarity"] = similarity
                    enhanced_metadata["retrieval_index"] = faiss_idx
                    
                    enhanced_doc = Document(
                        page_content=doc.page_content,
                        metadata=enhanced_metadata
                    )
                    documents.append(enhanced_doc)
        
        logger.debug(f"✅ Formatted {len(documents)} result documents")
        return documents
    
    def _search_chunks(self, query_embedding, top_k=5):
        """Search text chunks and return raw results with similarity scores."""
        logger.debug(f"🔍 Searching chunks for top_{top_k} results...")
        
        # Ensure query_embedding is properly shaped
        query_embedding = np.array(query_embedding).astype("float32")
        
        # Handle different input shapes
        if query_embedding.ndim == 1:
            query_embedding = query_embedding.reshape(1, -1)
        elif query_embedding.ndim > 2:
            query_embedding = query_embedding.reshape(1, -1)
        
        logger.debug(f"🔢 Query embedding shape: {query_embedding.shape}, Index dimension: {self.dimension}")
        print(f"[DEBUG] Query embedding final shape: {query_embedding.shape}")
        print(f"[DEBUG] Index dimension: {self.dimension}")
        
        # Verify dimensions match
        if query_embedding.shape[1] != self.dimension:
            logger.error(f"❌ Dimension mismatch: query {query_embedding.shape[1]} vs index {self.dimension}")
            raise ValueError(f"Query embedding dimension {query_embedding.shape[1]} doesn't match index dimension {self.dimension}")
        
        # Search FAISS index
        logger.debug("🔎 Executing FAISS search...")
        with tqdm(total=1, desc="🔎 FAISS search", unit="search", leave=False) as pbar:
            distances, indices = self.index.search(query_embedding, top_k)
            pbar.update(1)
        
        # Format results
        logger.debug("📋 Formatting chunk results...")
        formatted = []
        
        for i in tqdm(range(top_k), desc="🔗 Processing chunks", unit="chunk", leave=False):
            faiss_idx = indices[0][i]
            if faiss_idx != -1 and faiss_idx < len(self.chunks_dict):
                distance = distances[0][i]
                formatted.append({
                    'chunk_id': faiss_idx,
                    'text': self.chunks_dict[faiss_idx],
                    'distance': distance,
                    'similarity': float(distance) 
                })
        
        logger.debug(f"✅ Formatted {len(formatted)} chunk results")
        return formatted
    

    def save_index(self, file_path):
        """Save FAISS index and metadata to disk."""
        logger.info(f"💾 Saving FAISS index to {file_path}...")
        file_path=f'vectorstores/{file_path}'
        if self.index is None:
            logger.error("❌ No index to save")
            raise ValueError("No index to save")
        
        # Save FAISS index
        logger.info("💾 Saving FAISS index file...")
        with tqdm(total=1, desc="💾 Saving index", unit="file") as pbar:
            faiss.write_index(self.index, f"{file_path}.faiss")
            pbar.update(1)
        
        # Save metadata (enhanced to include reranking settings)
        logger.info("📋 Preparing metadata for saving...")
        metadata = {
            'chunks_dict': self.chunks_dict,
            'dimension': self.dimension,
            'total_vectors': self.total_vectors,
            'index_type': self.index_type,
            'docstore': self.docstore,
            'index_to_docstore_id': self.index_to_docstore_id,
            'documents': self.documents,
            'enable_reranking': self.enable_reranking
        }
        
        logger.info("💾 Saving metadata file...")
        with tqdm(total=1, desc="💾 Saving metadata", unit="file") as pbar:
            with open(f"{file_path}_metadata.pkl", 'wb') as f:
                pickle.dump(metadata, f)
            pbar.update(1)
        
        logger.info(f"✅ Index and metadata saved successfully to {file_path}")
        print(f"[FAISS] Index and metadata saved to {file_path}")
    
    def load_index(self, file_path, embedder_model=None):
        """Load FAISS index and metadata from disk."""
        file_path=f'vectorstores/{file_path}'
        logger.info(f"📂 Loading FAISS index from {file_path}...")
        
        # Check file existence
        if not os.path.exists(f"{file_path}.faiss"):
            logger.error(f"❌ Index file not found: {file_path}.faiss")
            raise FileNotFoundError(f"Index file {file_path}.faiss not found")
        
        if not os.path.exists(f"{file_path}_metadata.pkl"):
            logger.error(f"❌ Metadata file not found: {file_path}_metadata.pkl")
            raise FileNotFoundError(f"Metadata file {file_path}_metadata.pkl not found")
        
        # Load FAISS index
        logger.info("📂 Loading FAISS index file...")
        with tqdm(total=1, desc="📂 Loading index", unit="file") as pbar:
            self.index = faiss.read_index(f"{file_path}.faiss")
            pbar.update(1)
        
        # Load metadata
        logger.info("📋 Loading metadata file...")
        with tqdm(total=1, desc="📋 Loading metadata", unit="file") as pbar:
            with open(f"{file_path}_metadata.pkl", 'rb') as f:
                metadata = pickle.load(f)
            pbar.update(1)
        
        # Restore attributes
        logger.info("🔄 Restoring vectorstore attributes...")
        self.chunks_dict = metadata['chunks_dict']
        self.dimension = metadata['dimension']
        self.total_vectors = metadata['total_vectors']
        self.index_type = metadata['index_type']
    
    
        # Set embedder model if provided
        if embedder_model:
            logger.info("🔧 Setting embedder model...")
            self.embedder_model = embedder_model
        
        enhanced_mode = "enabled" if self.docstore is not None else "disabled"
        reranking_status = "enabled" if self.enable_reranking else "disabled"
        
        logger.info(f"✅ Index loaded successfully: {self.total_vectors} vectors, dim {self.dimension}")
        logger.info(f"🔧 Enhanced docstore mode: {enhanced_mode}")
        logger.info(f"🎯 Reranking: {reranking_status}")
        
        print(f"[FAISS] Index loaded: {self.total_vectors} vectors, dim {self.dimension}")
        if self.docstore is not None:
            print(f"[FAISS] Enhanced docstore mode enabled")
        if self.enable_reranking:
            print(f"[FAISS] Reranking enabled")
        
        return self