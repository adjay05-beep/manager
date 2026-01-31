from db import service_supabase
from utils.logger import log_error

class StorageRepository:
    """
    Handles all direct interactions with Supabase Storage buckets.
    """
    @staticmethod
    def upload_file(bucket_name, path, file_content, content_type):
        """Upload a file to a specific bucket."""
        # Using service_supabase's manual storage manager for stability
        return service_supabase.storage.upload(bucket_name, path, file_content, content_type)

    @staticmethod
    def get_public_url(bucket_name, path):
        """Get the public URL for a file."""
        return service_supabase.storage.get_public_url(bucket_name, path)

    @staticmethod
    def list_files(bucket_name, path=""):
        """List files in a bucket path."""
        return service_supabase.storage.list_files(bucket_name, path)

    @staticmethod
    def delete_file(bucket_name, path):
        """Delete a file from a bucket."""
        return service_supabase.storage.delete(bucket_name, path)
