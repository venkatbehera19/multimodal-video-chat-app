import yt_dlp
import os
import subprocess
import webvtt
from fastapi import status

from app.config.env_config import settings
from app.config.log_config import logger

from app.services.youtube_service import YoutubeService
from app.services.video_processing import VideoProcessing
from app.repository.lamma_repo import LammaRepository

class IngestionService:
  """Orchestrates the end-to-end media ingestion pipeline for YouTube content.

  This service handles the lifecycle of a video from URL to searchable assets,
  including metadata extraction, conditional downloading, audio stripping, 
  and visual frame extraction. It is designed to be used within a FastAPI 
  environment with persistent Docker volumes.

  Attributes:
    youtube_link (str): The valid YouTube URL to be processed.
    base_dir (str): Root directory for all uploaded and processed assets.
    video_dir (str): Sub-directory where raw .mp4 files are stored.
    audio_dir (str): Sub-directory for extracted .mp3 files and subtitles.
    frames_dir (str): Sub-directory for organized frame sequences (per video).
  """

  def __init__(self, youtube_link: str) -> None:
    """Intilize the Ingestion service Class
    
    Args:
      youtube_link: the youtube link the need to ingest

    Returns:
      None
    """
    self.youtube_link = youtube_link
    self.base_dir     = settings.UPLOAD_DIR
    self.video_dir    = os.path.join(self.base_dir, "videos")
    self.audio_dir    = os.path.join(self.base_dir, "audio")
    self.frames_dir   = os.path.join(self.base_dir, "frames_dir")
    self.cookies_path = "/app/cookies.txt"

    for d in [self.video_dir, self.audio_dir, self.frames_dir]:
      os.makedirs(d, exist_ok=True)

  async def process(self):
    """
    Multimodal Ingestion Pipeline:
    Downloads, parses, embeds, and indexes video (visuals) and audio (subtitles/transcript).
    """

    youtube_service = YoutubeService(self.youtube_link)
    youtube_file = youtube_service.download_file(self.video_dir)
    if not youtube_file:
      logger.info("File Not downloaded")
      return None

    vp = VideoProcessing(youtube_file['video'])
    video_frames_path = vp.process_video_frames()
    logger.info(f"video_frames_path {video_frames_path}")
    if not video_frames_path:
      logger.info("Can Not Process Frames")
      return None
  
    lr = LammaRepository()
    res = lr.add_data_to_qdrant(
      frame_input_path=video_frames_path["folder"],
      srt_path= youtube_file["subtitles"]
    )
    return {
      "status": "completed",
      "message": "Data indexed and local storage cleared.",
      "meta": youtube_file["meta"]["id"]
    }