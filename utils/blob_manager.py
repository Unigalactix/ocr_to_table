"""
Azure Blob Storage Manager
Handles all blob storage operations
"""
from azure.storage.blob import BlobServiceClient


class BlobManager:
    """
    Manages Azure Blob Storage operations for file management.
    """
    
    def __init__(self, connection_string, container_name):
        """
        Initialize blob manager.
        
        Args:
            connection_string (str): Azure blob storage connection string
            container_name (str): Container name
        """
        if not connection_string:
            raise ValueError("Blob storage connection string is required")
        
        self.connection_string = connection_string
        self.container_name = container_name
        self.blob_service_client = BlobServiceClient.from_connection_string(connection_string)
        self.container_client = self.blob_service_client.get_container_client(container_name)
    
    def list_files(self, extensions=None):
        """
        List files in the blob container.
        
        Args:
            extensions (list): File extensions to filter (e.g., ['.pdf', '.xlsx'])
            
        Returns:
            list: List of blob file names
        """
        if extensions is None:
            extensions = ['.pdf', '.png', '.jpg', '.jpeg', '.bmp', '.tiff', '.tif', '.csv', '.xlsx', '.xls']
        
        try:
            blobs = []
            for blob in self.container_client.list_blobs():
                if any(blob.name.lower().endswith(ext.lower()) for ext in extensions):
                    blobs.append(blob.name)
            return blobs
        except Exception as e:
            raise RuntimeError(f"Failed to list blobs: {e}")
    
    def download_file(self, blob_name):
        """
        Download a file from blob storage.
        
        Args:
            blob_name (str): Name of the blob to download
            
        Returns:
            bytes: File content as bytes
        """
        try:
            blob_client = self.blob_service_client.get_blob_client(
                container=self.container_name, 
                blob=blob_name
            )
            return blob_client.download_blob().readall()
        except Exception as e:
            raise RuntimeError(f"Failed to download blob '{blob_name}': {e}")
    
    def file_exists(self, blob_name):
        """
        Check if a file exists in blob storage.
        
        Args:
            blob_name (str): Name of the blob to check
            
        Returns:
            bool: True if file exists
        """
        try:
            blob_client = self.blob_service_client.get_blob_client(
                container=self.container_name, 
                blob=blob_name
            )
            return blob_client.exists()
        except Exception:
            return False
