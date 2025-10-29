# ingestion/indexer.py
from sqlitedict import SqliteDict
import os
INDEX_DB = os.path.join(os.path.dirname(__file__), "index.sqlite")

def list_records():
    with SqliteDict(INDEX_DB) as db:
        return dict(db)
