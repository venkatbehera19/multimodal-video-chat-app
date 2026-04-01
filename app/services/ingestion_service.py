import yt_dlp
import os
import subprocess
import webvtt
from fastapi import status

from app.config.env_config import settings
from app.config.log_config import logger
from app.utils.embedding_utils import image_embeddings_client
from app.repository.factory import image_embedding_vector_store, text_embedding_vector_store

from moviepy.video.io.VideoFileClip import VideoFileClip
from langchain_core.documents import Document
from app.utils.ingest import get_video_details, download_file, download_subtitle, extract_audio, frames_to_image_vectors, cleanup_local_files

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

  def extract_frames_ffmpeg(self, video_path: str, fps: int = 1):
    """Uses FFmpeg to extract frames at a specific rate
    (default 1 frame per second).
    """
    video_filename = os.path.basename(video_path)
    video_name = os.path.splitext(video_filename)[0]

    output_dir = f"{self.frames_dir}/{video_name}"
    os.makedirs(output_dir, exist_ok=True)
    output_pattern = os.path.join(output_dir, "frame_%04d.jpg")

    command = [
      'ffmpeg',
      '-i', video_path,
      '-vf', f'fps={fps}',
      '-q:v', '2',
      output_pattern,
      '-y' 
    ]

    try:
      logger.info(f"Extraction from video to frames to {output_dir} started")
      subprocess.run(command, check=True, capture_output=True, text=True)
      logger.info(f"Successfully extracted frames to {output_dir}")
      return output_dir
    except subprocess.CalledProcessError as e:
      logger.info(f"FFMPEG error: {e}")
      return None
    except Exception as e:
      logger.info(f"Error during frames extraction: {e}")
      return None

  async def process_video_frames(self, video_path: str):
    """Process the video into image frames

    Args:
      video_path: path to the video handled
    """
    frames_path = self.extract_frames_ffmpeg(video_path, fps=1)
    if frames_path:
      extracted_images = sorted(os.listdir(frames_path))
      return {
        "folder": frames_path,
        "count": len(extracted_images),
        "sample_image": extracted_images[0] if extracted_images else None
      }
    return {"error": "Extraction failed"}
  
  def _extract_timestamp(self, frame_path: str) -> int:
    """Helper to get second from frame filename (e.g., frame_0001.jpg -> 1s)"""
    try:
      filename = os.path.basename(frame_path)
      frame_num = int(filename.split('_')[1].split('.')[0])
      return frame_num # Assuming 1 FPS extraction
    except:
      return 0

  def parse_vtt_to_documents(self, file_path: str, video_id: str) -> list[Document]:
    """Parses a VTT file and groups lines into manageable Document chunks."""
    documents = []
    try:
      for caption in webvtt.read(file_path):
        clean_text = caption.text.replace('\n', ' ').strip()

        if not clean_text:
          continue

        doc = Document(
          page_content=clean_text,
          metadata={
            "video_id": video_id,
            "start_time": caption.start,
            "end_time": caption.end,
            "source": file_path,
            "type": "subtitle"
          }
        )
        documents.append(doc)
      return documents
    
    except Exception as e:
      logger.info(f"Error parsing VTT: {e}")
      return []

  async def process(self):
    """
    Multimodal Ingestion Pipeline:
    Downloads, parses, embeds, and indexes video (visuals) and audio (subtitles/transcript).
    """

    meta = get_video_details(self.youtube_link, self.cookies_path)
    if not meta:
      logger.error("Failed to fetch video metadata. Aborting.")
      return {"status": "error", "message": "Metadata fetch failed"}, status.HTTP_200_OK
    
    video_id        = meta['video_id']
    logger.info(f"Starting processing for Video ID: {video_id}")

    if image_embedding_vector_store.video_exists(video_id) and \
      text_embedding_vector_store.file_exists(video_id):
      logger.info(f"Video {video_id} fully indexed. Skipping re-processing.")
      return {"video_id": video_id, "status": "already_indexed"}, status.HTTP_200_OK
    
    downloaded_file = download_file(self.video_dir, self.youtube_link, self.cookies_path)
    if not downloaded_file:
      return {"status": "error", "message": "Video download failed"}, status.HTTP_200_OK
    
    caption_path = None
    if meta.get("has_english_subtitles") or meta.get("has_auto_generated_en"):
      caption_path = download_subtitle(self.audio_dir, video_id, self.youtube_link, self.cookies_path)

    audio_path = None
    if not caption_path:
      logger.info(f"No captions. Extracting audio for transcription...")
      audio_path = extract_audio(self.audio_dir, downloaded_file)
      # TODO: subtitle_docs = self.transcribe_audio(audio_path)

    frame_results = await self.process_video_frames(downloaded_file)
    image_vectors = frames_to_image_vectors(frame_results, video_id)

    if image_vectors and not image_embedding_vector_store.video_exists(video_id):
      try:
        image_embedding_vector_store.add_vectors(image_vectors)
        logger.info("Image embeddings successfully indexed.")
      except Exception as e:
        logger.error(f"Image indexing failed: {e}")

    if caption_path and not text_embedding_vector_store.video_exists(video_id):
      subtitle_docs = self.parse_vtt_to_documents(caption_path, video_id)
      if subtitle_docs:
        try:
          text_embedding_vector_store.add_documents(subtitle_docs)
          logger.info("Subtitles successfully indexed.")
        except Exception as e:
          logger.error(f"Subtitle indexing failed: {e}")

    files_to_delete = [downloaded_file, audio_path, caption_path]
    frames_folder = frame_results.get("folder")
    cleanup_local_files(files_to_delete, frames_folder)

    return {
      "video_id": video_id,
      "status": "completed",
      "message": "Data indexed and local storage cleared."
    }