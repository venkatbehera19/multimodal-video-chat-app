import base64
from app.config.log_config import logger

def get_base64_image(image_path):
    """ get the image path and give the base64 image for that path"""
    try:
        with open(image_path, "rb") as img_file:
            return base64.b64encode(img_file.read()).decode('utf-8')
    except Exception as e:
        logger.info(f"Error while getting the base64 images {str(e)}")
        return None