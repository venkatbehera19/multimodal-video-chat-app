from fastapi import APIRouter, status
from app.services.ingestion_service import IngestionService

router = APIRouter(tags=['rag'])

@router.post('/upload', status_code=status.HTTP_201_CREATED)
async def ingest_link(youtube_link: str):
  """Create an ingestion request
  
  Args:
    youtube_link: youtube link that needs to chart with.

  Returns:
    Ingestion response with message
  """

  ingestion_service = IngestionService(youtube_link= youtube_link)
  response = await ingestion_service.process()
  return response
