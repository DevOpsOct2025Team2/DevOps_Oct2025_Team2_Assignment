import logging
from datetime import datetime, timezone

from app.services.supabase_client import get_supabase_client

logger = logging.getLogger(__name__)

ALLOWED_SORT_FIELDS = {"created_at", "filename", "file_size"}
FILE_STORAGE_BUCKET = "user-files"


def _sanitize_for_log(value):
    if value is None:
        return ""
    if not isinstance(value, str):
        value = str(value)
    return value.replace("\r", "").replace("\n", "")


def _build_storage_path(user_id, file_id):
    """Build a deterministic storage path for a file in Supabase Storage."""
    return f"{user_id}/{file_id}"


class FileService:
    def __init__(self, supabase_client=None):
        self.supabase = supabase_client or get_supabase_client()

    def get_user_files(
        self, user_id, page=1, per_page=10, sort_by="created_at", sort_order="desc"
    ):
        try:
            if not user_id or not isinstance(user_id, str):
                return {"files": [], "error": "Invalid user ID"}

            if page < 1 or per_page < 1 or per_page > 100:
                return {"files": [], "error": "Invalid pagination parameters"}

            if sort_by not in ALLOWED_SORT_FIELDS:
                sort_by = "created_at"

            if sort_order not in ("asc", "desc"):
                sort_order = "desc"

            query = self.supabase.table("files").select("*", count="exact")
            query = query.eq("owner_id", user_id)
            query = query.order(sort_by, desc=(sort_order == "desc"))

            start = (page - 1) * per_page
            end = start + per_page - 1
            query = query.range(start, end)

            response = query.execute()

            files = []
            if response.data:
                for file in response.data:
                    files.append(
                        {
                            "id": file.get("id"),
                            "filename": file.get("filename"),
                            "file_size": file.get("file_size", 0),
                            "file_type": file.get("file_type"),
                            "created_at": file.get("created_at"),
                        }
                    )

            return {
                "files": files,
                "page": page,
                "per_page": per_page,
                "total": response.count or 0,
            }
        except Exception:
            logger.exception("Error retrieving user files")
            return {"files": [], "error": "Failed to retrieve files"}

    def get_file_metadata(self, file_id):
        """Retrieve file metadata from the database by file ID.

        Returns the file record dict on success, or None if not found.
        """
        if not file_id or not isinstance(file_id, str):
            return None

        try:
            response = (
                self.supabase.table("files")
                .select("id, owner_id, filename, file_size, file_type, created_at")
                .eq("id", file_id)
                .single()
                .execute()
            )
        except Exception:
            logger.debug(
                "Error fetching file metadata for file_id=%s",
                _sanitize_for_log(file_id),
            )
            return None

        if not response or not response.data:
            return None

        file_data = response.data
        if isinstance(file_data, list) and len(file_data) > 0:
            file_data = file_data[0]
        elif not isinstance(file_data, dict):
            return None

        return file_data

    def get_file_for_download(self, user_id, file_id):
        """Retrieve a file for download after verifying ownership.

        Returns a dict with either:
          - 'file_bytes', 'filename', 'file_type', 'file_size' on success
          - 'error' key with an error description on failure
          - 'forbidden' key set to True when ownership check fails
        """
        if not user_id or not isinstance(user_id, str):
            return {"error": "Invalid user ID"}

        if not file_id or not isinstance(file_id, str):
            return {"error": "Invalid file ID"}

        # Step 1: Get file metadata
        file_data = self.get_file_metadata(file_id)
        if not file_data:
            return {"error": "File not found"}

        # Step 2: Verify ownership
        if file_data.get("owner_id") != user_id:
            safe_file_id = _sanitize_for_log(file_id)
            safe_user_id = _sanitize_for_log(user_id)
            safe_owner_id = _sanitize_for_log(file_data.get("owner_id"))
            logger.warning(
                "Unauthorized download attempt: user_id=%s tried to download file_id=%s owned by %s",
                safe_user_id,
                safe_file_id,
                safe_owner_id,
            )
            return {
                "error": "You do not have permission to download this file",
                "forbidden": True,
            }

        # Step 3: Download file bytes from Supabase Storage
        storage_path = _build_storage_path(user_id, file_id)
        try:
            file_bytes = self.supabase.storage.from_(FILE_STORAGE_BUCKET).download(
                storage_path
            )
        except Exception as exc:
            exc_str = str(exc).lower()
            is_not_found = (
                "not found" in exc_str or "not_found" in exc_str or "404" in exc_str
            )
            if is_not_found:
                logger.warning(
                    "File not in storage (legacy upload?): file_id=%s path=%s",
                    _sanitize_for_log(file_id),
                    _sanitize_for_log(storage_path),
                )
                return {
                    "error": "This file was uploaded before download support was enabled. "
                    "Please delete it and re-upload to enable downloads."
                }
            logger.exception(
                "Error downloading file from storage: file_id=%s path=%s",
                _sanitize_for_log(file_id),
                _sanitize_for_log(storage_path),
            )
            return {"error": "Failed to download file from storage"}

        if file_bytes is None:
            logger.error(
                "Storage returned None for file_id=%s path=%s",
                _sanitize_for_log(file_id),
                _sanitize_for_log(storage_path),
            )
            return {"error": "File content not found in storage"}

        return {
            "file_bytes": file_bytes,
            "filename": file_data.get("filename") or "download",
            "file_type": file_data.get("file_type") or "application/octet-stream",
            "file_size": file_data.get("file_size") or 0,
        }

    def delete_file(self, user_id, file_id):
        try:
            if not user_id or not isinstance(user_id, str):
                return {"error": "Invalid user ID"}

            if not file_id or not isinstance(file_id, str):
                return {"error": "Invalid file ID"}

            # verify file belongs to user
            try:
                file_check = (
                    self.supabase.table("files")
                    .select("id", "owner_id")
                    .eq("id", file_id)
                    .single()
                    .execute()
                )
            except Exception:
                logger.debug("Error checking file ownership")
                return {"error": "File not found"}

            if not file_check or not file_check.data:
                return {"error": "File not found"}

            # extract file data (handle both dict and list responses)
            file_data = file_check.data
            if isinstance(file_data, list) and len(file_data) > 0:
                file_data = file_data[0]
            elif not isinstance(file_data, dict):
                return {"error": "File not found"}

            if file_data.get("owner_id") != user_id:
                safe_file_id = _sanitize_for_log(file_id)
                safe_user_id = _sanitize_for_log(user_id)
                logger.warning(
                    "Unauthorized delete attempt file_id=%s user_id=%s",
                    safe_file_id,
                    safe_user_id,
                )
                return {"error": "Unauthorized"}

            # Delete from Supabase Storage first
            storage_path = _build_storage_path(user_id, file_id)
            try:
                self.supabase.storage.from_(FILE_STORAGE_BUCKET).remove([storage_path])
            except Exception:
                logger.warning(
                    "Failed to remove file from storage (continuing with DB delete): path=%s",
                    _sanitize_for_log(storage_path),
                )

            self.supabase.table("files").delete().eq("id", file_id).execute()
            return {"success": True, "message": "File deleted successfully"}
        except Exception:
            logger.exception("Error deleting file")
            return {"error": "Failed to delete file"}

    def upload_file(
        self,
        user_id,
        filename,
        file_data,
        file_type="application/octet-stream",
        username=None,
    ):
        try:
            if not user_id or not isinstance(user_id, str):
                return {"error": "Invalid user ID"}

            if not filename or not isinstance(filename, str):
                return {"error": "Invalid filename"}
            if file_data is None:
                return {"error": "Missing file data"}

            # normalize file_data to bytes
            if hasattr(file_data, "read"):
                file_bytes = file_data.read()
            else:
                file_bytes = file_data
            if isinstance(file_bytes, memoryview):
                file_bytes = file_bytes.tobytes()
            if not isinstance(file_bytes, (bytes, bytearray)):
                return {"error": "Invalid file data"}

            file_size = len(file_bytes)

            if file_size == 0:
                return {"error": "File is empty"}

            if file_size > 50 * 1024 * 1024:
                return {"error": "File size exceeds limit"}

            # store file metadata in db
            db_response = (
                self.supabase.table("files")
                .insert(
                    {
                        "owner_id": user_id,
                        "filename": filename,
                        "file_size": file_size,
                        "file_type": file_type,
                    }
                )
                .execute()
            )

            if not db_response.data:
                return {"error": "Failed to save file metadata"}

            file_id = db_response.data[0].get("id")

            # upload binary to Supabase Storage
            storage_path = _build_storage_path(user_id, file_id)
            try:
                self.supabase.storage.from_(FILE_STORAGE_BUCKET).upload(
                    storage_path,
                    file_bytes,
                    {"content-type": file_type},
                )
            except Exception:
                logger.exception(
                    "Failed to upload file to storage, rolling back DB record"
                )
                # Roll back the metadata record on storage failure
                try:
                    self.supabase.table("files").delete().eq("id", file_id).execute()
                except Exception:
                    logger.exception(
                        "Failed to roll back file metadata after storage error"
                    )
                return {"error": "Failed to upload file to storage"}

            return {
                "id": file_id,
                "filename": filename,
                "file_size": file_size,
                "file_type": file_type,
            }
        except Exception:
            logger.exception("Error uploading file")
            return {"error": "Failed to upload file"}
