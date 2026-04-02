from langchain_groq import ChatGroq
from app.constants.app_constants import GROQ_CHAT_MODEL
from app.config.env_config import settings

class GroqChatClient:
  """Factory for Gemini chat model clients."""

  def __init__(self) -> None:
    """Initialize with model name and temperature from constants."""
    self.model_name = GROQ_CHAT_MODEL.MODEL_NAME.value
    self.temprature = GROQ_CHAT_MODEL.TEMPERATURE.value

  def create_client(self):
    """Create a Gemini chat model client.

    Returns:
      ChatGoogleGenerativeAI instance.
    """
    chat_client = ChatGroq(
      model = self.model_name,
      temperature = self.temprature,
      max_tokens=None,
      groq_proxy=settings.GROQ_API_KEY
    )

    return chat_client
  
default_chat_client = GroqChatClient().create_client()