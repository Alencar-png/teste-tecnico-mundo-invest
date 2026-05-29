from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.declarative import declarative_base

import os
import logging

logging.basicConfig()
logging.getLogger('sqlalchemy.engine').setLevel(logging.WARNING)

load_dotenv()


def _sqlite_engine():
    """Engine SQLite local (dev/testes), sem exigir banco no ar."""
    url = os.getenv('DATABASE_URL', 'sqlite:///./clientes.db')
    connect_args = {"check_same_thread": False} if url.startswith("sqlite") else {}
    return url, create_engine(url, connect_args=connect_args)


def get_engine():
    """Usa MySQL quando as variáveis MYSQL_* estão definidas (produção/docker);
    caso contrário cai para SQLite. Em testes (TESTING=1) força SQLite."""
    if os.getenv('TESTING') == '1':
        return _sqlite_engine()

    user = os.getenv('MYSQL_USER')
    password = os.getenv('MYSQL_PASSWORD')
    host = os.getenv('MYSQL_HOST')
    port = os.getenv('MYSQL_PORT')
    db = os.getenv('MYSQL_DATABASE')

    if all([user, password, host, port, db]):
        from sqlalchemy_utils import database_exists, create_database
        url = f"mysql+pymysql://{user}:{password}@{host}:{port}/{db}"
        if not database_exists(url):
            create_database(url)
        return url, create_engine(url)

    return _sqlite_engine()


url, engine = get_engine()

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()
