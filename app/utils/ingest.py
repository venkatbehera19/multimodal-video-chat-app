import base64
import yt_dlp
import os
import shutil
from app.config.log_config import logger
from app.utils.embedding_utils import image_embeddings_client


from moviepy.video.io.VideoFileClip import VideoFileClip

def get_base64_image(image_path: str) -> str:
    """Converts a local image file to a base64 string for DB storage.
    
    Args:
        image_path: path of the image file

    Returns:
        decoded base64 images
    """
    with open(image_path, "rb") as image_file:
        return base64.b64encode(image_file.read()).decode('utf-8')
    
def get_video_details(url: str,  cookies_path: str):
    """Extract the video information from the youtube URL File"""

    ydl_opts = {
        'quiet': True, 'no_warnings': True,
        'cookiefile': cookies_path if os.path.exists(cookies_path) else None
        }
    try:
      with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        logger.info(f" fetching the metadata of video link .....")

        info = ydl.extract_info(url, download=False)
        manual_subs = info.get('subtitles', {})
        auto_subs = info.get('automatic_captions', {})

        has_manual_en = any(key.startswith('en') for key in manual_subs.keys())
        has_auto_en = any(key.startswith('en') for key in auto_subs.keys())

        logger.info(f"fetched the metadata of video link .....")

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

def download_file(video_dir: str, url: str, cookies_path: str):
    """Download the file and save it the static file location
    
    Args:
        video_dir: directory that video wants to store
        url: youtube url that wants to download

    Return:
        location of the file that saved
    """

    ydl_opts = {
        'format': 'best[ext=mp4]', 
        'outtmpl': os.path.join(video_dir, '%(id)s.%(ext)s'),
        'noplaylist': True,
        'quiet': False,

        'writesubtitles': True,
        'writeautomaticsub': True,
        'subtitleslangs': ['en'], 
        'subtitlesformat': 'srt',
        'cookiefile': cookies_path if os.path.exists(cookies_path) else None
    }

    try:
        logger.info(f"Downloading the video from  {url}.")
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)

            video_file = ydl.prepare_filename(info)
            video_id = info.get("id")

            subtitle_file = None

            for file in os.listdir(video_dir):
                if file.startswith(video_id) and file.endswith(".srt"):
                    subtitle_file = os.path.join(video_dir, file)
                    break
            logger.info(f"Downloaded video: {video_file}")
            if subtitle_file:
                print(f"Downloaded subtitles: {subtitle_file}")
            else:
                print("No subtitles available")
            return {
                "video": video_file,
                "subtitles": subtitle_file,
                "meta": info
            }

    except Exception as e:
      logger.info(f"Error during audio extraction: {e}")
      return None
    
def download_subtitle(audio_dir: str, video_id: str, link: str, cookies_path: str):
    """Downloading the subtitle through video_id and link url
    
    Args:
        audio_dir: directory that audio need to save
        video_id: uniq video id that created by Youtube and fetched from youtube meta
    Returns:
      downloaded subtitle path
    """
    try:
        ydl_opts = {
            'skip_download': True,       
            'writesubtitles': True,      
            'writeautomaticsub': True, 
            'subtitleslangs': ['en.*'],
            'outtmpl': f'{audio_dir}/{video_id}.%(ext)s',
            'postprocessors': [{
            'key': 'FFmpegSubtitlesConvertor',
            'format': 'vtt',
            }],
            'quiet': True,
            'cookiefile': cookies_path if os.path.exists(cookies_path) else None

        }
        logger.info(f"English subtitles found for {video_id}. Downloading...")
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([link])

        expected_path = f"{audio_dir}/{video_id}.en.vtt"
        return expected_path if os.path.exists(expected_path) else None
    except Exception as e:
        logger.info(f"Unable to download the subtitles {str(e)}")
        return None
    
def extract_audio(audio_dir: str, video_path: str):
    """This method help in for extracting the audio track from the video file and
    and save it as a MP3
    
    Returns:
      audio file path
    """
    video_name = os.path.splitext(os.path.basename(video_path))[0]
    audio_path = os.path.join(audio_dir, f"{video_name}.mp3")

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
    
def extract_timestamp(frame_path: str) -> int:
    """Helper to get second from frame filename (e.g., frame_0001.jpg -> 1s)"""
    try:
        filename = os.path.basename(frame_path)
        frame_num = int(filename.split('_')[1].split('.')[0])
        return frame_num # Assuming 1 FPS extraction
    except:
        return 0
    
def frames_to_image_vectors(frame_results, video_id: str):
    """"""
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
                    "vector": image_vector,
                    "timestamp": extract_timestamp(frame_path),
                    "base64": get_base64_image(frame_path)
                    }
                )
                
            except Exception as e:
                logger.error(f"Failed to embed frame {frame_path}: {e}")
                return []
        return image_vectors
    return []

def cleanup_local_files(files_to_remove: list, folder_to_remove: str = None):
    """
    Cleans up temporary processing files and directories.
    
    Args:
        files_to_remove (list): List of paths to individual files (e.g., .mp4, .mp3).
        folder_to_remove (str): Path to the frames directory to be deleted recursively.
    """
    logger.info("Starting cleanup of local temporary assets...")
    for file_path in files_to_remove:
        if file_path and os.path.exists(file_path):
            try:
                os.remove(file_path)
                logger.debug(f"Removed temporary file: {file_path}")
            except Exception as e:
                logger.error(f"Failed to delete file {file_path}: {e}")

    if folder_to_remove and os.path.exists(folder_to_remove):
        try:
            shutil.rmtree(folder_to_remove)
            logger.debug(f"Removed frames directory: {folder_to_remove}")
        except Exception as e:
            logger.error(f"Failed to delete folder {folder_to_remove}: {e}")

    logger.info("Cleanup complete.")