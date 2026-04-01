import yt_dlp
import os
import subprocess

from app.config.env_config import settings
from app.config.log_config import logger
from app.utils.embedding_utils import image_embeddings_client

from moviepy.video.io.VideoFileClip import VideoFileClip

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

    for d in [self.video_dir, self.audio_dir, self.frames_dir]:
      os.makedirs(d, exist_ok=True)

  def get_video_details(self):
    """Extract the video information from the youtube URL File"""

    ydl_opts = {'quiet': True, 'no_warnings': True}
    try:
      with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(self.youtube_link, download=False)
        manual_subs = info.get('subtitles', {})
        auto_subs = info.get('automatic_captions', {})

        has_manual_en = any(key.startswith('en') for key in manual_subs.keys())
        has_auto_en = any(key.startswith('en') for key in auto_subs.keys())
        # logger.info(f" fetching the metadata of video link {str(e)} .....")
        return {
          "video_id": info.get("id"),
          "title": info.get("title"),
          "has_english_subtitles": has_manual_en,
          "has_auto_generated_en": has_auto_en,
          "manual_languages": list(manual_subs.keys()),
          "auto_languages": list(auto_subs.keys())
        }
    except Exception as e:
      logger.info(f"Error while fetching the metadata of video link {str(e)} .....")

  def download_file(self):
    """Download the file and save it the static file location"""
    ydl_opts = {
      'format': 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best',
      'outtmpl': f'{self.video_dir}/%(id)s.%(ext)s',
      'noplaylist': True,
      'quiet': False,
    }

    try:
      with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        logger.info(f"Downloading the video from  {self.youtube_link}. Ingestion Service... download_file")
        info = ydl.extract_info(self.youtube_link, download=True)
        filename = ydl.prepare_filename(info)
        return filename
      
    except Exception as e:
      logger.info(f"Error during audio extraction: {e}")
      return None
    
  def download_subtitle(self, video_id: str):
    """Downloading the subtitle through video_id and link url
    
    Returns:
      downloaded subtitle path
    """
    try:
      ydl_opts = {
        'skip_download': True,       
        'writesubtitles': True,      
        'writeautomaticsub': True, 
        'subtitleslangs': ['en.*'],
        'outtmpl': f'{self.audio_dir}/{video_id}.%(ext)s',
        'postprocessors': [{
          'key': 'FFmpegSubtitlesConvertor',
          'format': 'vtt',
        }],
        'quiet': True,
      }

      with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        ydl.download([self.youtube_link])

      expected_path = f"{self.audio_dir}/{video_id}.en.vtt"
      return expected_path if os.path.exists(expected_path) else None
    except Exception as e:
      logger.info(f"Unable to download the subtitles {str(e)}")
      return None
    
  def extract_audio(self, video_path: str):
    """This method help in for extracting the audio track from the video file and
    and save it as a MP3
    
    Returns:
      audio file path
    """
    video_name = os.path.splitext(os.path.basename(video_path))[0]
    audio_path = os.path.join(self.audio_dir, f"{video_name}.mp3")

    if os.path.exists(audio_path):
      return audio_path
    
    try: 
      with VideoFileClip(video_path) as video:
        if video.audio is not None:
          logger.info(f"Downloading the audio from  {video_path}. Ingestion Service... extract_audio")
          video.audio.write_audiofile(audio_path, logger=None)
          return audio_path
        else:
          logger.info(f"Warning: No audio track found in {video_path}")
          return None
      
    except Exception as e:
      logger.info(f"Error during audio extraction: {e}")
      return None

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
    """"""
    logger.info("LOgging for video extractions")
    frames_path = self.extract_frames_ffmpeg(video_path, fps=1)
    if frames_path:
      extracted_images = sorted(os.listdir(frames_path))
      return {
        "folder": frames_path,
        "count": len(extracted_images),
        "sample_image": extracted_images[0] if extracted_images else None
      }
    return {"error": "Extraction failed"}

  async def process(self):
    """Process the youtube link with bellow process
    
    Steps:
      1. download the video
      2. save it to the local file
      -> 3 steps (
          1. caption less video ( image embedding )
          2. video to audio (speach to text model)
          3. fps
        )
      3. then extract the images from the video and save it to the output folder
      4. convert the video into audio and save it to the output folder
      5. then convert the audio into text file
      6. then construct the multimodel index and vector stores
      7. creating diffrent collection for image and text and add it to the vector db
    """
    downloaded_file = self.download_file()
    logger.info(f"Downloaded File {downloaded_file}. Ingestion Service...")
    meta = self.get_video_details()
    video_id = meta['video_id']

    caption_path = None
    if meta["has_english_subtitles"] or meta["has_auto_generated_en"]:
      logger.info(f"English subtitles found for {video_id}. Downloading...")
      caption_path = self.download_subtitle(video_id)
    else:
      logger.info(f"No English subtitles found for {video_id}. Will rely on Audio/Vision.")

    audio_path = None
    if not caption_path:
      logger.info(f"No captions for {video_id}. Starting audio extraction...")
      audio_path = self.extract_audio(downloaded_file)

    frame_results = await self.process_video_frames(downloaded_file)
    logger.info(f"RESULT {frame_results}. Will rely on Audio/Vision.")
    frames_dir = frame_results.get("folder")

    image_vectors = []

    if frames_dir and os.path.exists(frames_dir):
      logger.info(f"Generating CLIP embeddings for frames in {frames_dir}...")

      frame_files = sorted([
        os.path.join(frames_dir, f) 
        for f in os.listdir(frames_dir) if f.endswith('.jpg')
      ])

      for frame_path in frame_files:
        try:
          image_vector = image_embeddings_client.embed_image([frame_path])[0]
          image_vectors.append(
            {
              "video_id": video_id,
              "frame_path": frame_path,
              "vector": image_vector
            }
          )
        except Exception as e:
          logger.error(f"Failed to embed frame {frame_path}: {e}")

    return {
      "video_id": video_id,
      "meta": meta,
      "paths": {
        "video": downloaded_file,
        "audio": audio_path,
        "subtitles": caption_path,
        "frames": frame_results.get("folder")
      },
      "embeddings_count": len(image_vectors)
    }