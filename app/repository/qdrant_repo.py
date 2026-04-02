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
from qdrant_client.http import models as rest_models

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

    vector_size = self._get_vector_size()

    if not self.client.collection_exists(self.collection_name):
      self.client.create_collection(
        collection_name=self.collection_name,
        vectors_config=models.VectorParams(
          size=vector_size,
          distance=models.Distance.COSINE
        ),
        on_disk_payload=True
      )
      logger.info(f"Hybrid collection '{self.collection_name}' created.")

    self.vector_store = QdrantVectorStore(
      client=self.client,
      collection_name=self.collection_name,
      embedding=self.embeddings
    )

  def _get_vector_size(self):
    """Helper to get dimension size from the embedding model"""
    try:
      if hasattr(self.embeddings, "client"):
        return self.embeddings.client.get_sentence_embedding_dimension()
      return 512 if "clip" in str(type(self.embeddings)).lower() else 384
    except:
      return 384

  def add_documents(self, documents):
    """Adds documents using pure dense embeddings."""
    logger.info(f"Adding {len(documents)} documents to {self.collection_name}...")
      
    texts = [doc.page_content for doc in documents]
    metadatas = [doc.metadata for doc in documents]

    ids = [str(uuid.uuid4()) for _ in range(len(documents))]
    self.vector_store.add_texts(texts=texts, metadatas=metadatas, ids=ids)

    logger.info("Batch upload complete.")


  def search(self, query: str, k: int = 5):
    """Performs standard Similarity Search (Dense Vector Search)"""
    results = self.vector_store.similarity_search(query, k=k)
    return results
  
  def search_images(self, query: str, k: int = 2, video_id: str = None):
    """"""
    query_vector = self.embeddings.embed_query(query)
    query_filter = None

    # metadata filtering 
    if video_id:
      query_filter = models.Filter(
        must=[
          models.FieldCondition(
            key="video_id", 
            match=models.MatchValue(value=video_id)
          )
        ]
      )

    results = self.client.query_points(
      collection_name=self.collection_name,
      query=query_vector,
      query_filter=query_filter,
      limit=k,
      with_payload=True 
    ).points
    return results

  def file_exists(self, video_id: str) -> bool:
    """Queries Qdrant metadata to check if a file is already processed."""
    try:
      results, _ = self.client.scroll(
          collection_name=self.collection_name,
          scroll_filter=models.Filter(
              must=[
                  models.FieldCondition(
                      key="metadata.video_id", # Ensure this matches your metadata structure
                      match=models.MatchValue(value=video_id),
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
  def video_exists(self, video_id: str) -> bool:
    """Checks if any points with the given video_id already exist in the collection.
    
    Args:
      video_id: 
    """
    try:
      results, _ = self.client.scroll(
        collection_name=self.collection_name,
        scroll_filter=models.Filter(
            must=[
                models.FieldCondition(
                    key="video_id",
                    match=models.MatchValue(value=video_id),
                )
            ]
        ),
        limit=1,
        with_payload=False,
        with_vectors=False
      )
      return len(results) > 0
    except Exception as e:
      logger.error(f"Error checking existence in {self.collection_name}: {e}")
      return False


  def add_vectors(self, vectors_data: list):
    """Pushes pre-computed vectors and metadata to Qdrant.
    
    Args:
        vectors_data (list): List of dicts containing 'vector', 'frame_path', 
        timestamp', and 'video_id'.
    """
    logger.info(f"Preparing to push {len(vectors_data)} image vectors to {self.collection_name}")
    points = []
    for data in vectors_data:
      point_id = str(uuid.uuid4())
      points.append(
        rest_models.PointStruct(
          id=point_id,
          vector=data["vector"],
          payload={
              "video_id": data["video_id"],
              "frame_path": data["frame_path"],
              "timestamp": data["timestamp"],
              "base64_image": data["base64"],
              "metadata": {
                "filename": os.path.basename(data["frame_path"]),
                "type": "video_frame"
              }
          }
        )
      )

    batch_size = 20
    for i in range(0, len(points), batch_size):
      self.client.upsert(
        collection_name=self.collection_name,
        points=points[i : i + batch_size],
        wait=True
      )
    
    logger.info(f"Successfully pushed {len(points)} points to Qdrant.")