import yt_dlp
import os

class YoutubeService:
    """"""
    def __init__(self, url: str):
        """"""
        self.url = url
        self.cookies_path = "/app/cookies.txt"

    def download_file(self, video_dir: str):
        """Download YouTube video + subtitles (if available)

        Args:
            video_dir: directory where files will be stored
            url: YouTube video URL

        Returns:
            dict with video path and subtitle path
        """
        os.makedirs(video_dir, exist_ok=True)

        ydl_opts = {
            'format': 'best[ext=mp4]', 
            'outtmpl': os.path.join(video_dir, '%(id)s.%(ext)s'),
            'noplaylist': True,
            'quiet': False,

            'writesubtitles': True,
            'writeautomaticsub': True,
            'subtitleslangs': ['en'],  
            'subtitlesformat': 'srt',
            'cookiefile': self.cookies_path if os.path.exists(self.cookies_path) else None
        }

        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(self.url, download=True)

                video_file = ydl.prepare_filename(info)
                video_id = info.get("id")

                subtitle_file = None

                for file in os.listdir(video_dir):
                    if file.startswith(video_id) and file.endswith(".srt"):
                        subtitle_file = os.path.join(video_dir, file)
                        break

                print(f"Downloaded video: {video_file}")
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
            print(f"Error during download: {e}")
            return None