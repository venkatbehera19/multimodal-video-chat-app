import os
from fastapi import FastAPI
from app.middleware.log_middleware import LoggingMiddleware
from app.config.log_config import logger

from app.exceptions import AppError
from app.exceptions.handlers import app_error_handler, global_exception_handler
from app.routes.ingestion_routes import router as ingestion_router
from app.routes.chat_routes import router as chat_router
from app.routes.image_routes import router as image_router

app = FastAPI(title="Rag API")
app.add_exception_handler(AppError, app_error_handler)
app.add_exception_handler(Exception, global_exception_handler)
app.add_middleware(LoggingMiddleware)

@app.get('/')
def health():
  logger.info("🚀 Application started")
  return { "status": 'ok' }

app.include_router(ingestion_router)
app.include_router(chat_router)
app.include_router(image_router)