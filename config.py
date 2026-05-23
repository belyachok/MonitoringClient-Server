import os
from datetime import timedelta

class Config:
    # Основные настройки
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'dev-secret-key-2023'
    
    # Настройки PostgreSQL
    DB_HOST = os.environ.get('DB_HOST') or 'localhost'
    DB_NAME = os.environ.get('DB_NAME') or 'monitoring_system'
    DB_USER = os.environ.get('DB_USER') or 'postgres'
    DB_PASSWORD = os.environ.get('DB_PASSWORD') or '123'
    DB_PORT = os.environ.get('DB_PORT') or '5432'
    
    # Настройки приложения
    MAX_REPORT_HOURS = 4
    UPLOAD_FOLDER = 'uploads'
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB max file size
    
    @property
    def DATABASE_URI(self):
        return f"dbname='{self.DB_NAME}' user='{self.DB_USER}' password='{self.DB_PASSWORD}' host='{self.DB_HOST}' port='{self.DB_PORT}'"

config = Config()