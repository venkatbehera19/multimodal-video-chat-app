from .qdrant_repo import QdrantRepository

from app.constants.app_constants import VECTOR_DB
from app.config.env_config import settings
from app.utils.embedding_utils import embeddings_client, image_embeddings_client

class VectorStoreFactory:
  """Dynamically selects and initializes the vector DB repository based on settings."""

  def __init__(self, embeddings, collection_name):
    """Intializing the varaibles that will be used inside the class"""
    self._repositories = {
      VECTOR_DB.QDRANT.value: QdrantRepository
    }
    self.db_type = settings.VECTOR_DB_TYPE.lower()
    self.embedding_client = embeddings
    self.collection_name = collection_name

  def get_repository(self):
    """return the vector store according to the configuration."""
    repo_class = self._repositories.get(self.db_type)

    if not repo_class:
      raise ValueError(f"Unsupported Vector DB type: {self.db_type}")
    
    if self.db_type == VECTOR_DB.QDRANT.value:
      return repo_class(
        embeddings =self.embedding_client,
        collection_name=self.collection_name
      )
    

image_embedding_vector_store = VectorStoreFactory(image_embeddings_client, VECTOR_DB.IMAGES_COLLECTION_NAME.value).get_repository()
text_embedding_vector_store = VectorStoreFactory(embeddings_client, VECTOR_DB.SUBTITLES_COLLECTION_NAME.value).get_repository()