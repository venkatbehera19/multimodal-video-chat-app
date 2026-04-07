import os
import imageio_ffmpeg
import subprocess

class VideoProcessing:
    """"""
    def __init__(self, video_path: str):
        """"""
        self.video_path = video_path
        self.video_filename = os.path.basename(self.video_path)
        self.video_name = os.path.splitext(self.video_filename)[0]

    def extract_frames_ffmpeg(self, fps: int = 1):
        """"""
        base_dir = os.path.dirname(self.video_path)
        output_dir = f"{base_dir}/{self.video_name}"
        os.makedirs(output_dir, exist_ok=True)
        output_pattern = os.path.join(output_dir, "frame_%04d.jpg")
        ffmpeg_path = imageio_ffmpeg.get_ffmpeg_exe()

        command = [
            ffmpeg_path,
            '-i', self.video_path,
            '-vf', f'fps={fps}',
            '-q:v', '2',
            output_pattern,
            '-y' 
        ]

        try:
            print(f"Extraction from video to frames to {output_dir} started")
            subprocess.run(command, check=True, capture_output=True, text=True)
            print(f"Successfully extracted frames to {output_dir}")
            return output_dir
        except subprocess.CalledProcessError as e:
            print(f"FFMPEG error: {e}")
            return None
        except Exception as e:
            print(f"Error during frames extraction: {e}")
            return None
        
    def process_video_frames(self):
        frames_path = self.extract_frames_ffmpeg(fps=1)
        if frames_path:
            extracted_images = sorted(os.listdir(frames_path))
            return {
                "folder": frames_path,
                "count": len(extracted_images),
                "sample_image": extracted_images[0] if extracted_images else None
            }
        return {"error": "Extraction failed"}