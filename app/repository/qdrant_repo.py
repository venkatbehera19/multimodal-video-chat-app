import os
from app.config.log_config import logger
from app.config.env_config import settings
from langchain_qdrant import QdrantVectorStore

from qdrant_client import QdrantClient, models
from qdrant_client.http.models import Distance, VectorParams, SparseVectorParams
from app.utils.embedding_utils import embeddings_client
from app.constants.app_constants import VECTOR_DB

from langchain_core.documents import Document
import uuid

class QdrantRepository:
  """Qdrant vector database configuration"""
  def __init__(self, embeddings, collection_name, host = settings.QDRANT_HOST, port=settings.QDRANT_PORT, path = None):
    """Initialize the repo
    Args:
      embeddings: embedding model for vectorization
      collection_name: name of the collection
      host: Qdrant service name in docker-compose
      port: Qdrant port (default 6333)
      path: If using local storage instead of server (optional)
    """
    self.embeddings = embeddings
    self.collection_name = collection_name

    if path:
      self.client = QdrantClient(path=path)
      logger.info(f"Qdrant initialized locally at {path}")
    else:
      self.client = QdrantClient(host=host, port=port)
      logger.info(f"Qdrant connecting to {host}:{port}")

    if not self.client.collection_exists(self.collection_name):
      self.client.create_collection(
        collection_name= self.collection_name,
        vectors_config={
          "dense": models.VectorParams(
            size=self.client.get_embedding_size(VECTOR_DB.EMBEDDING_MODEL.value),
            distance=models.Distance.COSINE
          )
        },
        sparse_vectors_config= {
          "sparse": models.SparseVectorParams()
        }
      )
      logger.info(f"Hybrid collection '{self.collection_name}' created.")

    self.vector_store = QdrantVectorStore(
      client=self.client,
      collection_name=self.collection_name,
      embedding=self.embeddings,
      vector_name="dense"
    )

  def add_documents(self, documents):
    """Add the document using the add_documents method"""
    logger.info(f"Adding {len(documents)} docs with Qdrant Hybrid Search...")

    embad_documents = []
    metadata = []

    for doc in documents:
      embad_documents.append({
        "dense": models.Document(text=doc.page_content, model=VECTOR_DB.EMBEDDING_MODEL.value),
        "sparse": models.Document(text=doc.page_content, model=VECTOR_DB.SPARSE_MODEL.value),
      })

      payload = doc.metadata.copy()
      payload["page_content"] = doc.page_content
      metadata.append(payload)

    self.client.upload_collection(
      collection_name=self.collection_name,
      vectors=embad_documents,
      payload=metadata,
      parallel=4, 
    )

    logger.info(f"Added {len(embad_documents)} docs with Qdrant Hybrid Search...")


  def search(self, query, k=5):
    """Performs Hybrid Search using Reciprocal Rank Fusion (RRF)"""
    results = self.client.query_points(
      collection_name= self.collection_name,
      query=models.FusionQuery(
        fusion=models.Fusion.RRF
      ),
      prefetch=[
        models.Prefetch(
          query=models.Document(text=query, model=VECTOR_DB.EMBEDDING_MODEL.value),
          using="dense",
        ),
        models.Prefetch(
          query=models.Document(text=query, model=VECTOR_DB.SPARSE_MODEL.value),
          using="sparse",
        ),
      ],
      query_filter=None, 
      limit=k
    ).points
  
    return [
          Document(
              page_content=res.payload['page_content'], 
              metadata=res.payload 
          ) for res in results
    ]


  def file_exists(self, filename: str) -> bool:
    """Efficiently queries Qdrant metadata using the Scroll API."""
    try:
      results, _ = self.client.scroll(
        collection_name=self.collection_name,
        scroll_filter=models.Filter(
          must=[
            models.FieldCondition(
              key="metadata.filename",
              match=models.MatchValue(value=filename),
            )
          ]
        ),
        limit=1,
        with_payload=False,
        with_vectors=False
      )
      return len(results) > 0
    except Exception as e:
      logger.error(f"Error checking Qdrant for file: {e}")
      return False