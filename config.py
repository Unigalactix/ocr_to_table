"""
Azure Configuration Manager
Handles all Azure service configurations and credentials
"""
import os
from dotenv import load_dotenv
from azure.ai.formrecognizer import DocumentAnalysisClient
from azure.core.credentials import AzureKeyCredential
from azure.storage.blob import BlobServiceClient


class AzureConfig:
    """
    Loads and manages Azure configuration from environment variables.
    Provides clients for Document Intelligence and Blob Storage.
    """
    
    def __init__(self):
        """Initialize Azure configuration from environment variables."""
        load_dotenv()
        
        self.doc_intelligence_endpoint = os.getenv('DOC_INTELLIGENCE_ENDPOINT')
        self.doc_intelligence_key = os.getenv('DOC_INTELLIGENCE_KEY')
        self.blob_connection_string = os.getenv('AZURE_BLOB_CONNECTION_STRING')
        self.blob_container = os.getenv('AZURE_BLOB_CONTAINER')
        
        # Validate required credentials
        if not (self.doc_intelligence_endpoint and self.doc_intelligence_key):
            raise ValueError("Azure Document Intelligence credentials are required")
    
    def get_document_client(self):
        """Create and return DocumentAnalysisClient instance."""
        try:
            return DocumentAnalysisClient(
                endpoint=self.doc_intelligence_endpoint,
                credential=AzureKeyCredential(self.doc_intelligence_key)
            )
        except Exception as e:
            raise RuntimeError(f"Failed to create Document Intelligence client: {e}")
    
    def get_blob_service_client(self):
        """Create and return BlobServiceClient instance if credentials available."""
        if not self.blob_connection_string:
            return None
        try:
            return BlobServiceClient.from_connection_string(self.blob_connection_string)
        except Exception as e:
            raise RuntimeError(f"Failed to create Blob Storage client: {e}")
    
    def has_blob_storage(self):
        """Check if blob storage credentials are configured."""
        return bool(self.blob_connection_string and self.blob_container)
