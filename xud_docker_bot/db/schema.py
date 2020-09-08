from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import Column, Integer, String, DateTime

Base = declarative_base()


class Image(Base):
    __tablename__ = 'images'

    digest = Column(String)
    repo = Column(String)
    tag = Column()
    branch = Column(String)
    platform = Column(String)
    commit1 = Column(String)
    commit2 = Column(String)
    size = Column(String)
    last_synced = Column(DateTime)
