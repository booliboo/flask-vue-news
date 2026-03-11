import os

class Config:

    BASE_DIR = os.path.abspath(os.path.dirname(__file__))

    SQLALCHEMY_DATABASE_URI = 'mysql+pymysql://root:0910@localhost:3306/news_db'
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    SECRET_KEY = "graduation_project_2026_key"

    UPLOAD_FOLDER = os.path.join(BASE_DIR, "uploads")

    SERVER_URL = "http://127.0.0.1:5000"

    JWT_EXPIRE_HOURS = 24