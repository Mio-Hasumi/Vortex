

"""
firebase.py
===========

Firebase Admin SDK adapter for authentication and Firestore access.
Provides high-level interface for user management and data persistence.
"""

from __future__ import annotations

import json
import logging
import os
from typing import Any, Dict, List, Optional, Union

import firebase_admin
from firebase_admin import auth, credentials, firestore, storage
from firebase_admin.exceptions import FirebaseError
from google.cloud.firestore_v1 import DocumentReference, DocumentSnapshot

from infrastructure.config import settings

logger = logging.getLogger(__name__)


class FirebaseAdminService:
    """
    High-level helper around Firebase Admin SDK (Auth + Firestore + Storage).
    Implements singleton pattern to ensure single app initialization.
    """

    _instance: Optional["FirebaseAdminService"] = None
    _app: Optional[firebase_admin.App] = None
    _db: Optional[firestore.Client] = None
    _storage_bucket: Optional[storage.Bucket] = None

    def __new__(cls) -> "FirebaseAdminService":
        """
        Singleton factory function
        """
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._init_app()
        return cls._instance

    def _init_app(self) -> None:
        """
        Initialize Firebase Admin SDK app
        """
        if self._app is not None:
            return
        
        try:
            # Try to get existing app
            self._app = firebase_admin.get_app()
            logger.info("✅ Using existing Firebase app")
        except ValueError:
            # Create new app with credentials
            if settings.FIREBASE_PROJECT_ID:
                # Production: use service account credentials
                cred_dict = {
                    "type": "service_account",
                    "project_id": settings.FIREBASE_PROJECT_ID,
                    "private_key_id": settings.FIREBASE_PRIVATE_KEY_ID,
                    "private_key": settings.FIREBASE_PRIVATE_KEY.replace('\\n', '\n'),
                    "client_email": settings.FIREBASE_CLIENT_EMAIL,
                    "client_id": settings.FIREBASE_CLIENT_ID,
                    "auth_uri": settings.FIREBASE_AUTH_URI,
                    "token_uri": settings.FIREBASE_TOKEN_URI,
                    "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
                    "client_x509_cert_url": settings.FIREBASE_CLIENT_X509_CERT_URL
                }
                
                cred = credentials.Certificate(cred_dict)
                self._app = firebase_admin.initialize_app(cred, {
                    'projectId': settings.FIREBASE_PROJECT_ID,
                    'storageBucket': settings.RECORDING_BUCKET_NAME
                })
            else:
                # Development: use default credentials
                self._app = firebase_admin.initialize_app({
                    'projectId': settings.FIREBASE_PROJECT_ID
                })
            
            logger.info("✅ Firebase app initialized successfully")
        except Exception as e:
            logger.error(f"❌ Failed to initialize Firebase app: {e}")
            raise

    @property
    def db(self) -> firestore.Client:
        """Return cached Firestore client"""
        if self._db is None:
            self._db = firestore.client(app=self._app)
        return self._db

    @property
    def auth(self):
        """Expose firebase_admin.auth for convenience"""
        return auth

    @property
    def storage_bucket(self) -> storage.Bucket:
        """Return cached Storage bucket"""
        if self._storage_bucket is None:
            self._storage_bucket = storage.bucket(app=self._app)
        return self._storage_bucket

    def create_user(self, email: str, password: str, display_name: str) -> auth.UserRecord:
        """Create a new user in Firebase Auth"""
        try:
            user = auth.create_user(
                email=email,
                password=password,
                display_name=display_name,
                app=self._app
            )
            logger.info(f"✅ Created user: {user.uid}")
            return user
        except FirebaseError as e:
            logger.error(f"❌ Failed to create user: {e}")
            raise

    def get_user(self, uid: str) -> auth.UserRecord:
        """Fetch user by UID"""
        try:
            user = auth.get_user(uid, app=self._app)
            return user
        except FirebaseError as e:
            logger.error(f"❌ Failed to get user {uid}: {e}")
            raise

    def delete_user(self, uid: str) -> None:
        """Delete user by UID"""
        try:
            auth.delete_user(uid, app=self._app)
            logger.info(f"✅ Deleted user: {uid}")
        except FirebaseError as e:
            logger.error(f"❌ Failed to delete user {uid}: {e}")
            raise

    def verify_id_token(self, id_token: str) -> Dict[str, Any]:
        """Verify and decode Firebase ID token"""
        try:
            decoded_token = auth.verify_id_token(id_token, app=self._app)
            return decoded_token
        except FirebaseError as e:
            logger.error(f"❌ Failed to verify token: {e}")
            raise

    def add_document(self, collection_name: str, data: Dict[str, Any], document_id: Optional[str] = None) -> DocumentReference:
        """Add document to Firestore collection"""
        try:
            collection_ref = self.db.collection(collection_name)
            
            if document_id:
                doc_ref = collection_ref.document(document_id)
                doc_ref.set(data)
            else:
                doc_ref = collection_ref.add(data)[1]
            
            logger.info(f"✅ Added document to {collection_name}: {doc_ref.id}")
            return doc_ref
        except Exception as e:
            logger.error(f"❌ Failed to add document to {collection_name}: {e}")
            raise

    def get_document(self, collection_name: str, document_id: str) -> Optional[Dict[str, Any]]:
        """Get document from Firestore"""
        try:
            doc_ref = self.db.collection(collection_name).document(document_id)
            doc = doc_ref.get()
            
            if doc.exists:
                return doc.to_dict()
            return None
        except Exception as e:
            logger.error(f"❌ Failed to get document {document_id} from {collection_name}: {e}")
            raise

    def server_timestamp(self):
        """Return server timestamp for Firestore"""
        return firestore.SERVER_TIMESTAMP

    def query_documents(self, collection_name: str, filters: Optional[List[Dict[str, Any]]] = None, 
                       limit: Optional[int] = None, order_by: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Query documents from Firestore collection with optional filters
        
        Args:
            collection_name: Name of the collection
            filters: List of filter dictionaries with keys: field, operator, value
            limit: Maximum number of documents to return
            order_by: Field to order by
            
        Returns:
            List of document dictionaries
        """
        try:
            collection_ref = self.db.collection(collection_name)
            query = collection_ref
            
            # Apply filters
            if filters:
                for filter_dict in filters:
                    field = filter_dict['field']
                    operator = filter_dict['operator']
                    value = filter_dict['value']
                    query = query.where(field, operator, value)
            
            # Apply ordering
            if order_by:
                query = query.order_by(order_by)
            
            # Apply limit
            if limit:
                query = query.limit(limit)
            
            # Execute query
            docs = query.stream()
            
            results = []
            for doc in docs:
                doc_data = doc.to_dict()
                doc_data['id'] = doc.id  # Include document ID
                results.append(doc_data)
            
            logger.info(f"✅ Queried {len(results)} documents from {collection_name}")
            return results
            
        except Exception as e:
            logger.error(f"❌ Failed to query documents from {collection_name}: {e}")
            raise

    def update_document(self, collection_name: str, document_id: str, data: Dict[str, Any]) -> None:
        """Update document in Firestore"""
        try:
            doc_ref = self.db.collection(collection_name).document(document_id)
            doc_ref.update(data)
            logger.info(f"✅ Updated document {document_id} in {collection_name}")
        except Exception as e:
            logger.error(f"❌ Failed to update document {document_id} in {collection_name}: {e}")
            raise

    def delete_document(self, collection_name: str, document_id: str) -> None:
        """Delete document from Firestore"""
        try:
            doc_ref = self.db.collection(collection_name).document(document_id)
            doc_ref.delete()
            logger.info(f"✅ Deleted document {document_id} from {collection_name}")
        except Exception as e:
            logger.error(f"❌ Failed to delete document {document_id} from {collection_name}: {e}")
            raise

    def batch_operation(self):
        """Return a new batch operation for atomic writes"""
        return self.db.batch()

    def collection_exists(self, collection_name: str) -> bool:
        """Check if collection exists and has documents"""
        try:
            # Try to get one document from the collection
            docs = self.db.collection(collection_name).limit(1).stream()
            return len(list(docs)) > 0
        except Exception as e:
            logger.error(f"❌ Failed to check collection existence {collection_name}: {e}")
            return False

    def get_collection_size(self, collection_name: str) -> int:
        """Get the number of documents in a collection"""
        try:
            docs = self.db.collection(collection_name).stream()
            return len(list(docs))
        except Exception as e:
            logger.error(f"❌ Failed to get collection size {collection_name}: {e}")
            return 0
