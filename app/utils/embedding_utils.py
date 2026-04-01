from langchain_huggingface import HuggingFaceEmbeddings
from langchain_experimental.open_clip import OpenCLIPEmbeddings

from app.config.log_config import logger
from app.constants.app_constants import VECTOR_DB
from app.config.env_config import settings

class EmbeddingClient:
  """Factory class for embedding client"""

  def __init__(self, model_name: str = VECTOR_DB.EMBEDDING_MODEL.value) -> None:
    """Intilize the embedding client
    
    Args:
      model_name: Huggingface model name
    """
    self.model_name = model_name

  def create_embeddings(self):
    """create embeddings client for the vector database.
    
    Returns:
      HuggingFaceEmbeddings instance configured for the model.
    """
    encode_kwargs = {"normalize_embeddings": True}
    logger.info("Loading embedding model")

    model = HuggingFaceEmbeddings(
      model_name = self.model_name,
      encode_kwargs=encode_kwargs,
      model_kwargs={
          "token": settings.HF_TOKEN, 
          "trust_remote_code": True
      }
    )
    return model
  
  def create_image_embeddings(self):
    """Creates a Multimodal CLIP instance specifically for Video Frames.
    """
    logger.info("Loading Multimodal CLIP Model for Image Frames")
    return OpenCLIPEmbeddings(
      model_name=VECTOR_DB.IMAGE_EMBEDDING_MODEL.value,
      checkpoint=VECTOR_DB.IMAGE_EMBEDDING_CHECK_POINT.value
    )
  
embeddings_client = EmbeddingClient().create_embeddings()
image_embeddings_client = EmbeddingClient().create_image_embeddings()
