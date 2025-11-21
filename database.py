"""
Database Helper Functions

MongoDB helper functions ready to use in your backend code.
Import and use these functions in your API endpoints for database operations.
"""

from pymongo import MongoClient
from datetime import datetime, timezone
import os
from dotenv import load_dotenv
from typing import Union, Optional, Dict, Any
from pydantic import BaseModel

# Load environment variables from .env file
load_dotenv()

_client = None
db = None

database_url = os.getenv("DATABASE_URL")
database_name = os.getenv("DATABASE_NAME")

if database_url and database_name:
    _client = MongoClient(database_url)
    db = _client[database_name]

# Helper functions for common database operations
def create_document(collection_name: str, data: Union[BaseModel, dict]):
    """Insert a single document with timestamp"""
    if db is None:
        raise Exception("Database not available. Check DATABASE_URL and DATABASE_NAME environment variables.")

    # Convert Pydantic model to dict if needed
    if isinstance(data, BaseModel):
        data_dict = data.model_dump()
    else:
        data_dict = data.copy()

    data_dict['created_at'] = datetime.now(timezone.utc)
    data_dict['updated_at'] = datetime.now(timezone.utc)

    result = db[collection_name].insert_one(data_dict)
    return str(result.inserted_id)

def get_documents(collection_name: str, filter_dict: dict = None, limit: int = None):
    """Get documents from collection"""
    if db is None:
        raise Exception("Database not available. Check DATABASE_URL and DATABASE_NAME environment variables.")
    
    cursor = db[collection_name].find(filter_dict or {})
    if limit:
        cursor = cursor.limit(limit)
    
    return list(cursor)

# New helpers
def get_document_by_id(collection_name: str, doc_id: str) -> Optional[Dict[str, Any]]:
    if db is None:
        raise Exception("Database not available. Check DATABASE_URL and DATABASE_NAME environment variables.")
    from bson import ObjectId
    try:
        return db[collection_name].find_one({"_id": ObjectId(doc_id)})
    except Exception:
        return None


def update_document(collection_name: str, doc_id: str, updates: dict) -> bool:
    if db is None:
        raise Exception("Database not available. Check DATABASE_URL and DATABASE_NAME environment variables.")
    from bson import ObjectId
    updates = updates.copy()
    updates['updated_at'] = datetime.now(timezone.utc)
    res = db[collection_name].update_one({"_id": ObjectId(doc_id)}, {"$set": updates})
    return res.modified_count > 0


def delete_document(collection_name: str, doc_id: str) -> bool:
    if db is None:
        raise Exception("Database not available. Check DATABASE_URL and DATABASE_NAME environment variables.")
    from bson import ObjectId
    res = db[collection_name].delete_one({"_id": ObjectId(doc_id)})
    return res.deleted_count > 0
