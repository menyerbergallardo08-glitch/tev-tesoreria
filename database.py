import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, 'tev_tesoreria.db')

# Soporte híbrido: Si existe DATABASE_URL (ej. Supabase / PostgreSQL en la nube), se conecta allá.
# De lo contrario, usa SQLite localmente en tu computadora.
RAW_DB_URL = os.environ.get('DATABASE_URL', f'sqlite:///{DB_PATH}')

# SQLAlchemy requiere 'postgresql://' en lugar de 'postgres://' que a veces entregan los proveedores
if RAW_DB_URL.startswith('postgres://'):
    DATABASE_URL = RAW_DB_URL.replace('postgres://', 'postgresql://', 1)
else:
    DATABASE_URL = RAW_DB_URL

if DATABASE_URL.startswith('sqlite'):
    engine = create_engine(
        DATABASE_URL,
        connect_args={'check_same_thread': False}
    )
else:
    engine = create_engine(
        DATABASE_URL,
        pool_pre_ping=True,
        pool_recycle=300
    )

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
