import os
import shutil

from fastapi import UploadFile, HTTPException
from app.constants.app_constants import ALLOWED_FILES
from app.config.log_config import logger
from app.config.env_config import settings

class FileProcessor:
  """Handles file validations and storage operations"""

  def __init__(self, file: UploadFile):
    """intialize with the uploaded file
    
    Args:
      file: FastAPI uploaded file instance
    """
    self.file = file

  def get_file_name(self)-> str:
    """Return the uploaded file name

    Return:
      Basename of the uploaded file
    """
    return os.path.basename(self.file.filename)

  def get_file_extension(self)-> str:
    """Return the uploaded file extaionsions

    Return:
      File extension including the dot (e.g. '.pdf').
    """
    return os.path.splitext(self.get_file_name())[1].lower()

  def get_file_path(self) -> str:
    """Build a validated destination path for the upload.

    Returns:
      Full path where the file should be save

    Raises:
      HTTPException: 400 if file extension is invalid, 500 if upload dir missing.
    """
    file_name = self.get_file_name()
    file_extension = self.get_file_extension()

    if not any(file_extension == ext.lower() for ext in ALLOWED_FILES.ALL_FILES.value):
      logger.info(f"Invalid file extesions uploaded {file_extension}")
      raise HTTPException(status_code=400, detail="Invlid file extensions")

    if not os.path.exists(settings.UPLOAD_DIR):
      logger.info(f"Upload directory not found:  {settings.UPLOAD_DIR}")
      raise HTTPException(status_code=500, detail="Upload directory is missing")

    file_path = os.path.join(settings.UPLOAD_DIR, file_name)
    logger.info(f"File Path: {file_path}")
    return file_path

  def save_file(self, file_path: str):
    """Save the file to the disk
    
    Args: 
      file_path: Destination path for the file.

    Returns: 
      The file path where the file was saved.
    """
    with open(file_path, 'wb') as f:
      shutil.copyfileobj(self.file.file, f)
    logger.info(f"File saved to: {file_path}")
    return file_path

  def delete_file(self, file_path: str):
    """Delete the file at the given path

    Args:
      file_path: Path to the file to delete.

    Returns:
      The deleted file path.
    """
    os.remove(file_path)
    logger.info(f"File deleted: {file_path}")
    return file_path