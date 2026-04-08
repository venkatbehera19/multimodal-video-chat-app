from fastapi import APIRouter, status, Query, HTTPException
from app.config.log_config import logger

from pathlib import Path
import base64

from pydantic import BaseModel
from typing import List

class ImagePathRequest(BaseModel):
    paths: List[str]

router = APIRouter(tags=['images'])

@router.post('/filepathimages', status_code=status.HTTP_200_OK)
def get_base_64_images(request: ImagePathRequest):
    """Accepts a list of file paths, reads the 
        images from the Docker filesystem,
        and returns them as base64 encoded strings.
    """
    encoded_images = []

    for image_path in request.paths:
        try:
            path = Path(image_path)

            if not path.exists():
                logger.warning(f"File not found: {image_path}")
                continue

            with open(path, "rb") as img_file:
                b64_string = base64.b64encode(img_file.read()).decode('utf-8')
                
                encoded_images.append({
                    "base64": b64_string,
                    "file_path": str(image_path),
                    "filename": path.name
                })

        except Exception as e:
            logger.error(f"Error encoding image {image_path}: {str(e)}")

    if not encoded_images and request.paths:
        raise HTTPException(
            status_code=404, 
            detail="None of the provided image paths could be processed."
        )

    return encoded_images
