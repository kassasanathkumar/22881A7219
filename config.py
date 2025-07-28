import os

basedir = os.path.abspath(os.path.dirname(__file__))

class Config:
    # SQLite DB path
    SQLALCHEMY_DATABASE_URI = 'sqlite:///' + os.path.join(basedir, 'shortener.db')
    
    # Disable event system for performance (unless you need it)
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # Secret key for session handling / CSRF (if needed)
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'you-will-never-guess'
