from llama_index.multi_modal_llms.gemini import GeminiMultiModal
from app.constants.app_constants import GEMINI_CHAT_MODEL
from app.config.env_config import settings

class GeminiMultimoadlClient:
  """Factory for Gemini chat model clients."""

  def __init__(self) -> None:
    """Initialize with model name and temperature from constants."""
    self.model_name = GEMINI_CHAT_MODEL.MODEL_NAME.value
    self.temprature = GEMINI_CHAT_MODEL.TEMPERATURE.value

  def create_client(self):
    """Create a Gemini chat model client.

    Returns:
      ChatGoogleGenerativeAI instance.
    """
    chat_client = GeminiMultiModal(
      model = self.model_name,
      temperature = self.temprature,
      max_tokens=None,
      api_key=settings.GEMINI_API_KEY
    )

    return chat_client
  
gemini_default_chat_client = GeminiMultimoadlClient().create_client()