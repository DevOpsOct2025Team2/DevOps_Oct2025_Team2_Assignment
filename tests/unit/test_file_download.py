"""Unit tests for FileService.get_file_for_download and get_file_metadata."""

from unittest.mock import MagicMock, patch

import pytest

from app.services.file_service import (
    FILE_STORAGE_BUCKET,
    FileService,
    _build_storage_path,
)


@pytest.fixture
def mock_supabase():
    return MagicMock()


class TestBuildStoragePath:
    """Tests for the _build_storage_path helper."""

    def test_basic_path(self):
        assert _build_storage_path("user1", "file1") == "user1/file1"

    def test_uuid_style_ids(self):
        uid = "a1b2c3d4-e5f6-7890-abcd-ef1234567890"
        fid = "f9e8d7c6-b5a4-3210-fedc-ba0987654321"
        assert _build_storage_path(uid, fid) == f"{uid}/{fid}"


class TestGetFileMetadata:
    """Tests for FileService.get_file_metadata."""

    def test_returns_metadata_dict(self, mock_supabase):
        expected = {
            "id": "file1",
            "owner_id": "user1",
            "filename": "report.pdf",
            "file_size": 2048,
            "file_type": "application/pdf",
            "created_at": "2024-06-01T12:00:00Z",
        }

        query = MagicMock()
        query.eq.return_value = query
        query.single.return_value = query
        query.execute.return_value = MagicMock(data=expected)
        mock_supabase.table.return_value.select.return_value = query

        service = FileService(mock_supabase)
        result = service.get_file_metadata("file1")

        assert result == expected
        mock_supabase.table.assert_called_with("files")

    def test_returns_none_when_not_found(self, mock_supabase):
        query = MagicMock()
        query.eq.return_value = query
        query.single.return_value = query
        query.execute.return_value = MagicMock(data=None)
        mock_supabase.table.return_value.select.return_value = query

        service = FileService(mock_supabase)
        result = service.get_file_metadata("nonexistent")

        assert result is None

    def test_returns_none_for_invalid_id(self, mock_supabase):
        service = FileService(mock_supabase)

        assert service.get_file_metadata(None) is None
        assert service.get_file_metadata("") is None
        assert service.get_file_metadata(123) is None

    def test_returns_none_on_db_exception(self, mock_supabase):
        query = MagicMock()
        query.eq.return_value = query
        query.single.return_value = query
        query.execute.side_effect = Exception("DB error")
        mock_supabase.table.return_value.select.return_value = query

        service = FileService(mock_supabase)
        result = service.get_file_metadata("file1")

        assert result is None

    def test_handles_list_response(self, mock_supabase):
        """Supabase can return a list even with .single() in edge cases."""
        expected = {
            "id": "file1",
            "owner_id": "user1",
            "filename": "doc.txt",
            "file_size": 100,
            "file_type": "text/plain",
            "created_at": "2024-01-01T00:00:00Z",
        }

        query = MagicMock()
        query.eq.return_value = query
        query.single.return_value = query
        query.execute.return_value = MagicMock(data=[expected])
        mock_supabase.table.return_value.select.return_value = query

        service = FileService(mock_supabase)
        result = service.get_file_metadata("file1")

        assert result == expected

    def test_returns_none_for_unexpected_data_type(self, mock_supabase):
        query = MagicMock()
        query.eq.return_value = query
        query.single.return_value = query
        query.execute.return_value = MagicMock(data="unexpected string")
        mock_supabase.table.return_value.select.return_value = query

        service = FileService(mock_supabase)
        result = service.get_file_metadata("file1")

        assert result is None


class TestGetFileForDownload:
    """Tests for FileService.get_file_for_download."""

    def _setup_metadata(self, mock_supabase, file_data):
        """Helper: configure supabase to return given file metadata."""
        query = MagicMock()
        query.eq.return_value = query
        query.single.return_value = query
        query.execute.return_value = MagicMock(data=file_data)
        mock_supabase.table.return_value.select.return_value = query

    def test_invalid_user_id_returns_error(self, mock_supabase):
        service = FileService(mock_supabase)

        for bad_uid in [None, "", 123, [], {}]:
            result = service.get_file_for_download(bad_uid, "file1")
            assert "error" in result
            assert result["error"] == "Invalid user ID"

    def test_invalid_file_id_returns_error(self, mock_supabase):
        service = FileService(mock_supabase)

        for bad_fid in [None, "", 123, [], {}]:
            result = service.get_file_for_download("user1", bad_fid)
            assert "error" in result
            assert result["error"] == "Invalid file ID"

    def test_file_not_found_returns_error(self, mock_supabase):
        self._setup_metadata(mock_supabase, None)

        service = FileService(mock_supabase)
        result = service.get_file_for_download("user1", "nonexistent")

        assert "error" in result
        assert result["error"] == "File not found"
        assert "forbidden" not in result

    def test_ownership_violation_returns_forbidden(self, mock_supabase):
        """User attempting to download another user's file gets forbidden."""
        file_data = {
            "id": "file1",
            "owner_id": "other_user",
            "filename": "secret.pdf",
            "file_size": 1024,
            "file_type": "application/pdf",
            "created_at": "2024-01-01T00:00:00Z",
        }
        self._setup_metadata(mock_supabase, file_data)

        service = FileService(mock_supabase)
        result = service.get_file_for_download("attacker_user", "file1")

        assert "error" in result
        assert result.get("forbidden") is True
        assert "permission" in result["error"].lower()

    def test_successful_download(self, mock_supabase):
        """Owner successfully downloads their own file."""
        file_data = {
            "id": "file1",
            "owner_id": "user1",
            "filename": "report.pdf",
            "file_size": 2048,
            "file_type": "application/pdf",
            "created_at": "2024-06-01T00:00:00Z",
        }
        self._setup_metadata(mock_supabase, file_data)

        expected_bytes = b"%PDF-1.4 fake pdf content here"
        storage_bucket = MagicMock()
        storage_bucket.download.return_value = expected_bytes
        mock_supabase.storage.from_.return_value = storage_bucket

        service = FileService(mock_supabase)
        result = service.get_file_for_download("user1", "file1")

        assert "error" not in result
        assert result["file_bytes"] == expected_bytes
        assert result["filename"] == "report.pdf"
        assert result["file_type"] == "application/pdf"
        assert result["file_size"] == 2048

        expected_path = _build_storage_path("user1", "file1")
        storage_bucket.download.assert_called_once_with(expected_path)
        mock_supabase.storage.from_.assert_called_once_with(FILE_STORAGE_BUCKET)

    def test_storage_download_exception_returns_error(self, mock_supabase):
        """Storage failure after ownership check returns a download error."""
        file_data = {
            "id": "file1",
            "owner_id": "user1",
            "filename": "doc.txt",
            "file_size": 100,
            "file_type": "text/plain",
            "created_at": "2024-01-01T00:00:00Z",
        }
        self._setup_metadata(mock_supabase, file_data)

        storage_bucket = MagicMock()
        storage_bucket.download.side_effect = Exception("Storage unavailable")
        mock_supabase.storage.from_.return_value = storage_bucket

        service = FileService(mock_supabase)
        result = service.get_file_for_download("user1", "file1")

        assert "error" in result
        assert "storage" in result["error"].lower()
        assert "forbidden" not in result

    def test_storage_returns_none_gives_error(self, mock_supabase):
        """Storage returning None (missing file) is handled gracefully."""
        file_data = {
            "id": "file1",
            "owner_id": "user1",
            "filename": "gone.zip",
            "file_size": 500,
            "file_type": "application/zip",
            "created_at": "2024-01-01T00:00:00Z",
        }
        self._setup_metadata(mock_supabase, file_data)

        storage_bucket = MagicMock()
        storage_bucket.download.return_value = None
        mock_supabase.storage.from_.return_value = storage_bucket

        service = FileService(mock_supabase)
        result = service.get_file_for_download("user1", "file1")

        assert "error" in result
        assert "not found" in result["error"].lower()

    def test_default_filename_when_missing(self, mock_supabase):
        """If metadata has no filename, the result uses a default."""
        file_data = {
            "id": "file1",
            "owner_id": "user1",
            "filename": None,
            "file_size": 0,
            "file_type": None,
            "created_at": "2024-01-01T00:00:00Z",
        }
        self._setup_metadata(mock_supabase, file_data)

        storage_bucket = MagicMock()
        storage_bucket.download.return_value = b"content"
        mock_supabase.storage.from_.return_value = storage_bucket

        service = FileService(mock_supabase)
        result = service.get_file_for_download("user1", "file1")

        assert "error" not in result
        assert result["filename"] == "download"
        assert result["file_type"] == "application/octet-stream"

    def test_different_users_different_files(self, mock_supabase):
        """Each user can only download files they own."""
        service = FileService(mock_supabase)

        # User A's file
        file_a = {
            "id": "fileA",
            "owner_id": "userA",
            "filename": "a.txt",
            "file_size": 10,
            "file_type": "text/plain",
            "created_at": "2024-01-01T00:00:00Z",
        }

        # User B tries to download User A's file
        self._setup_metadata(mock_supabase, file_a)
        result = service.get_file_for_download("userB", "fileA")

        assert "error" in result
        assert result.get("forbidden") is True

    def test_ownership_check_is_exact_match(self, mock_supabase):
        """owner_id comparison is strict: 'user1' != 'user10'."""
        file_data = {
            "id": "file1",
            "owner_id": "user1",
            "filename": "exact.txt",
            "file_size": 10,
            "file_type": "text/plain",
            "created_at": "2024-01-01T00:00:00Z",
        }
        self._setup_metadata(mock_supabase, file_data)

        service = FileService(mock_supabase)

        result = service.get_file_for_download("user10", "file1")
        assert "error" in result
        assert result.get("forbidden") is True

    def test_download_binary_content_types(self, mock_supabase):
        """Various binary file types download correctly."""
        test_cases = [
            ("image.png", "image/png", b"\x89PNG\r\n"),
            ("archive.zip", "application/zip", b"PK\x03\x04"),
            (
                "spreadsheet.xlsx",
                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                b"PK",
            ),
        ]

        for filename, file_type, content in test_cases:
            file_data = {
                "id": "file1",
                "owner_id": "user1",
                "filename": filename,
                "file_size": len(content),
                "file_type": file_type,
                "created_at": "2024-01-01T00:00:00Z",
            }
            self._setup_metadata(mock_supabase, file_data)

            storage_bucket = MagicMock()
            storage_bucket.download.return_value = content
            mock_supabase.storage.from_.return_value = storage_bucket

            service = FileService(mock_supabase)
            result = service.get_file_for_download("user1", "file1")

            assert "error" not in result, f"Failed for {filename}"
            assert result["file_bytes"] == content
            assert result["filename"] == filename
            assert result["file_type"] == file_type

    def test_large_file_download(self, mock_supabase):
        """Large file content is returned without truncation."""
        file_data = {
            "id": "bigfile",
            "owner_id": "user1",
            "filename": "large.bin",
            "file_size": 10 * 1024 * 1024,
            "file_type": "application/octet-stream",
            "created_at": "2024-01-01T00:00:00Z",
        }
        self._setup_metadata(mock_supabase, file_data)

        large_content = b"x" * (10 * 1024 * 1024)
        storage_bucket = MagicMock()
        storage_bucket.download.return_value = large_content
        mock_supabase.storage.from_.return_value = storage_bucket

        service = FileService(mock_supabase)
        result = service.get_file_for_download("user1", "bigfile")

        assert "error" not in result
        assert len(result["file_bytes"]) == 10 * 1024 * 1024

    def test_storage_path_uses_user_and_file_id(self, mock_supabase):
        """Verify the correct storage path is used for download."""
        file_data = {
            "id": "file99",
            "owner_id": "user42",
            "filename": "test.pdf",
            "file_size": 100,
            "file_type": "application/pdf",
            "created_at": "2024-01-01T00:00:00Z",
        }
        self._setup_metadata(mock_supabase, file_data)

        storage_bucket = MagicMock()
        storage_bucket.download.return_value = b"pdf bytes"
        mock_supabase.storage.from_.return_value = storage_bucket

        service = FileService(mock_supabase)
        service.get_file_for_download("user42", "file99")

        storage_bucket.download.assert_called_once_with("user42/file99")
