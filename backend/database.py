import os
import logging
from datetime import datetime
from typing import Any, Dict, List, Optional
from pymongo import MongoClient
from bson import ObjectId

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

MONGO_URL = os.getenv("DATABASE_URL", "mongodb://localhost:27017")
DB_NAME = os.getenv("DATABASE_NAME", "appdb")

_client = MongoClient(MONGO_URL)
db = _client[DB_NAME]


def _serialize_id(doc: Dict[str, Any]) -> Dict[str, Any]:
    if not doc:
        return doc
    if "_id" in doc:
        doc["id"] = str(doc.pop("_id"))
    return doc


def create_document(collection_name: str, data: Dict[str, Any]) -> Dict[str, Any]:
    now = datetime.utcnow()
    data = {**data, "created_at": now, "updated_at": now}
    result = db[collection_name].insert_one(data)
    created = db[collection_name].find_one({"_id": result.inserted_id})
    return _serialize_id(created)


def get_documents(collection_name: str, filter_dict: Optional[Dict[str, Any]] = None, limit: int = 100) -> List[Dict[str, Any]]:
    filter_dict = filter_dict or {}
    docs = list(db[collection_name].find(filter_dict).limit(limit))
    return [_serialize_id(d) for d in docs]


def get_document_by_id(collection_name: str, doc_id: str) -> Optional[Dict[str, Any]]:
    try:
        doc = db[collection_name].find_one({"_id": ObjectId(doc_id)})
        return _serialize_id(doc) if doc else None
    except Exception as e:
        logger.error(f"get_document_by_id error: {e}")
        return None


def update_document(collection_name: str, doc_id: str, data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    try:
        data["updated_at"] = datetime.utcnow()
        db[collection_name].update_one({"_id": ObjectId(doc_id)}, {"$set": data})
        return get_document_by_id(collection_name, doc_id)
    except Exception as e:
        logger.error(f"update_document error: {e}")
        return None


def delete_document(collection_name: str, doc_id: str) -> bool:
    try:
        res = db[collection_name].delete_one({"_id": ObjectId(doc_id)})
        return res.deleted_count > 0
    except Exception as e:
        logger.error(f"delete_document error: {e}")
        return False
