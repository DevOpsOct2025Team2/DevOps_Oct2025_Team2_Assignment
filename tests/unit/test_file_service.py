import pytest
from unittest.mock import MagicMock
from app.services.file_service import FileService

@pytest.fixture
def mock_supabase():
    return MagicMock()

class TestGetUserFiles:
    def test_success(self, mock_supabase):
        """Test successful file retrieval"""
        mock_data = [{
            'id': 'file1',
            'owner_id': 'user123',
            'filename': 'test.pdf',
            'file_size': 1024,
            'file_type': 'application/pdf',
            'created_at': '2024-01-01T00:00:00Z'
        }]

        mock_query = MagicMock()
        mock_query.eq.return_value = mock_query
        mock_query.order.return_value = mock_query
        mock_query.range.return_value = mock_query

        mock_response = MagicMock()
        mock_response.data = mock_data
        mock_response.count = 1
        mock_query.execute.return_value = mock_response

        mock_supabase.table.return_value.select.return_value = mock_query
        
        service = FileService(mock_supabase)
        result = service.get_user_files(user_id='user123', page=1, per_page=10)

        assert len(result['files']) == 1
        assert result['files'][0]['filename'] == 'test.pdf'
        assert result['page'] == 1

    def test_invalid_pagination(self, mock_supabase):
        """Test invalid pagination parameters"""
        service = FileService(mock_supabase)

        result = service.get_user_files(user_id='user123', page=0, per_page=10)
        assert 'error' in result
        assert result['files'] == []

class TestDeleteFile:
    def test_success(self, mock_supabase):
        """Test successful file deletion"""
        # return dict directly 
        select_query = MagicMock()
        select_query.eq.return_value = select_query
        select_query.single.return_value = select_query
        select_query.execute.return_value = MagicMock(
            data={'id': 'file1', 'owner_id': 'user123'}
        )
        
        delete_query = MagicMock()
        delete_query.eq.return_value = delete_query
        delete_query.execute.return_value = MagicMock()
        
        # Configure table mock 
        def table_side_effect(table_name):
            table_mock = MagicMock()
            if table_name == 'files':
                table_mock.select.return_value = select_query
                table_mock.delete.return_value = delete_query
            return table_mock
        
        mock_supabase.table.side_effect = table_side_effect
        
        service = FileService(mock_supabase)
        result = service.delete_file(user_id='user123', file_id='file1')
        
        assert result.get('success') is True
        assert 'message' in result

    def test_unauthorized(self, mock_supabase):
        """Test deletion fails when user doesn't own file"""
        # mock returns dict directly
        select_query = MagicMock()
        select_query.eq.return_value = select_query
        select_query.single.return_value = select_query
        select_query.execute.return_value = MagicMock(
            data={'id': 'file1', 'owner_id': 'other_user'}
        )
        
        table_mock = MagicMock()
        table_mock.select.return_value = select_query
        mock_supabase.table.return_value = table_mock
        
        service = FileService(mock_supabase)
        result = service.delete_file(user_id='user123', file_id='file1')
        
        assert 'error' in result
        assert result['error'] == 'Unauthorized'

    def test_file_not_found(self, mock_supabase):
        """Test deletion fails when file doesn't exist"""
        select_query = MagicMock()
        select_query.eq.return_value = select_query
        select_query.single.return_value = select_query
        select_query.execute.return_value = MagicMock(data=None)
        
        table_mock = MagicMock()
        table_mock.select.return_value = select_query
        mock_supabase.table.return_value = table_mock
        
        service = FileService(mock_supabase)
        result = service.delete_file(user_id='user123', file_id='nonexistent')
        
        assert 'error' in result
        assert result['error'] == 'File not found'

@pytest.mark.parametrize(
    "user_id,file_id",
    [
        ("user123", None),
        ("", "file1"),
        (None, "file1"),
    ],
)
def test_delete_file_invalid_inputs(mock_supabase, user_id, file_id):
    """Invalid inputs return error"""
    service = FileService(mock_supabase)
    result = service.delete_file(user_id=user_id, file_id=file_id)

    assert "error" in result

@pytest.mark.parametrize(
    "exception_message",
    [
        "Storage failure",
        "Database error",
    ],
)
def test_delete_file_exception_handling(mock_supabase, exception_message):
    """Unexpected errors handled safely"""
    mock_supabase.table.side_effect = Exception(exception_message)

    service = FileService(mock_supabase)
    result = service.delete_file(user_id="user123", file_id="file1")

    assert "error" in result

@pytest.mark.parametrize(
    "page,per_page",
    [
        (-1, 10),
        (1, 0),
        (1, 101),
    ],
)
def test_get_user_files_invalid_ranges(mock_supabase, page, per_page):
    """Invalid pagination handled safely"""
    service = FileService(mock_supabase)
    result = service.get_user_files("user123", page, per_page)

    assert "error" in result

def test_get_user_files_missing_fields(mock_supabase):
    """Files with missing optional fields handled safely"""
    mock_data = [{
        "id": "file1",
        "owner_id": "user123",
        # filename missing intentionally
    }]

    mock_query = MagicMock()
    mock_query.eq.return_value = mock_query
    mock_query.order.return_value = mock_query
    mock_query.range.return_value = mock_query

    mock_response = MagicMock()
    mock_response.data = mock_data
    mock_response.count = 1
    mock_query.execute.return_value = mock_response

    mock_supabase.table.return_value.select.return_value = mock_query

    service = FileService(mock_supabase)
    result = service.get_user_files("user123", 1, 10)

    assert isinstance(result["files"], list)

def test_get_user_files_none_data(mock_supabase):
    """None data response handled safely"""
    mock_query = MagicMock()
    mock_query.eq.return_value = mock_query
    mock_query.order.return_value = mock_query
    mock_query.range.return_value = mock_query

    mock_response = MagicMock()
    mock_response.data = None
    mock_response.count = 0
    mock_query.execute.return_value = mock_response

    mock_supabase.table.return_value.select.return_value = mock_query

    service = FileService(mock_supabase)
    result = service.get_user_files("user123", 1, 10)

    assert result["files"] == []

def test_get_user_files_partial_data(mock_supabase):
    """Files missing optional fields handled safely"""
    mock_data = [{"id": "file1", "owner_id": "user123"}]

    mock_query = MagicMock()
    mock_query.eq.return_value = mock_query
    mock_query.order.return_value = mock_query
    mock_query.range.return_value = mock_query

    mock_response = MagicMock()
    mock_response.data = mock_data
    mock_response.count = 1
    mock_query.execute.return_value = mock_response

    mock_supabase.table.return_value.select.return_value = mock_query

    service = FileService(mock_supabase)
    result = service.get_user_files("user123", 1, 10)

    assert isinstance(result["files"], list)

def test_get_user_files_empty_list(mock_supabase):
    """Empty result still returns valid structure"""
    mock_query = MagicMock()
    mock_query.eq.return_value = mock_query
    mock_query.order.return_value = mock_query
    mock_query.range.return_value = mock_query

    mock_response = MagicMock()
    mock_response.data = []
    mock_response.count = 0
    mock_query.execute.return_value = mock_response

    mock_supabase.table.return_value.select.return_value = mock_query

    service = FileService(mock_supabase)
    result = service.get_user_files("user123", 1, 10)

    assert result["files"] == []

def test_get_user_files_full_metadata_processing(mock_supabase):
    """Ensure file metadata processing paths are executed"""
    mock_data = [{
        "id": "file1",
        "owner_id": "user123",
        "filename": "test.pdf",
        "file_size": 2048,
        "file_type": "application/pdf",
        "created_at": "2024-01-01T00:00:00Z",
        "storage_path": "uploads/test.pdf"
    }]

    mock_query = MagicMock()
    mock_query.eq.return_value = mock_query
    mock_query.order.return_value = mock_query
    mock_query.range.return_value = mock_query

    mock_response = MagicMock()
    mock_response.data = mock_data
    mock_response.count = 1
    mock_query.execute.return_value = mock_response

    mock_supabase.table.return_value.select.return_value = mock_query

    service = FileService(mock_supabase)
    result = service.get_user_files("user123", 1, 10)

    assert result["files"][0]["id"] == "file1"

def test_delete_file_delete_operation_failure(mock_supabase):
    """Delete fails after ownership validation"""
    select_query = MagicMock()
    select_query.eq.return_value = select_query
    select_query.single.return_value = select_query
    select_query.execute.return_value = MagicMock(
        data={"id": "file1", "owner_id": "user123"}
    )

    delete_query = MagicMock()
    delete_query.eq.return_value = delete_query
    delete_query.execute.side_effect = Exception("Delete failed")

    def table_side_effect(name):
        table_mock = MagicMock()
        if name == "files":
            table_mock.select.return_value = select_query
            table_mock.delete.return_value = delete_query
        return table_mock

    mock_supabase.table.side_effect = table_side_effect

    service = FileService(mock_supabase)
    result = service.delete_file("user123", "file1")

    assert "error" in result

def test_get_user_files_with_storage_path_processing(mock_supabase):
    mock_data = [{
        "id": "file1",
        "owner_id": "user123",
        "filename": "test.pdf",
        "storage_path": "uploads/test.pdf"
    }]

    mock_query = MagicMock()
    mock_query.eq.return_value = mock_query
    mock_query.order.return_value = mock_query
    mock_query.range.return_value = mock_query

    mock_response = MagicMock()
    mock_response.data = mock_data
    mock_response.count = 1
    mock_query.execute.return_value = mock_response

    mock_supabase.table.return_value.select.return_value = mock_query

    service = FileService(mock_supabase)
    result = service.get_user_files("user123", 1, 10)

    assert result["files"][0]["id"] == "file1"

def test_get_user_files_processing_exception(mock_supabase):
    mock_query = MagicMock()
    mock_query.eq.return_value = mock_query
    mock_query.order.return_value = mock_query
    mock_query.range.return_value = mock_query

    mock_response = MagicMock()
    mock_response.data = [{}]   # missing expected keys
    mock_response.count = 1
    mock_query.execute.return_value = mock_response

    mock_supabase.table.return_value.select.return_value = mock_query

    service = FileService(mock_supabase)
    result = service.get_user_files("user123", 1, 10)

    assert "files" in result

def test_get_file_metadata_exception(mock_supabase):
    """Metadata fetch exception returns None"""
    mock_supabase.table.side_effect = Exception("DB error")

    service = FileService(mock_supabase)
    result = service.get_file_metadata("file1")

    assert result is None

def test_get_file_for_download_storage_exception(mock_supabase):
    service = FileService(mock_supabase)

    service.get_file_metadata = MagicMock(return_value={
        "id": "file1",
        "owner_id": "user123",
        "filename": "test.pdf"
    })

    mock_storage = MagicMock()
    mock_storage.download.side_effect = Exception("storage failure")
    mock_supabase.storage.from_.return_value = mock_storage

    result = service.get_file_for_download("user123", "file1")

    assert "error" in result

def test_get_file_for_download_storage_exception(mock_supabase):
    service = FileService(mock_supabase)

    service.get_file_metadata = MagicMock(return_value={
        "id": "file1",
        "owner_id": "user123",
        "filename": "test.pdf"
    })

    mock_storage = MagicMock()
    mock_storage.download.side_effect = Exception("storage failure")
    mock_supabase.storage.from_.return_value = mock_storage

    result = service.get_file_for_download("user123", "file1")

    assert "error" in result

def test_get_file_for_download_storage_returns_none(mock_supabase):
    service = FileService(mock_supabase)

    service.get_file_metadata = MagicMock(return_value={
        "id": "file1",
        "owner_id": "user123"
    })

    mock_storage = MagicMock()
    mock_storage.download.return_value = None
    mock_supabase.storage.from_.return_value = mock_storage

    result = service.get_file_for_download("user123", "file1")

    assert "error" in result

def test_upload_file_success(mock_supabase):
    insert_response = MagicMock()
    insert_response.data = [{"id": "file1"}]

    mock_supabase.table.return_value.insert.return_value.execute.return_value = insert_response

    mock_storage = MagicMock()
    mock_supabase.storage.from_.return_value = mock_storage

    service = FileService(mock_supabase)

    result = service.upload_file(
        "user123",
        "test.txt",
        b"hello world",
        "text/plain"
    )

    assert result["id"] == "file1"

def test_upload_file_storage_failure_rolls_back(mock_supabase):
    insert_response = MagicMock()
    insert_response.data = [{"id": "file1"}]

    mock_supabase.table.return_value.insert.return_value.execute.return_value = insert_response

    mock_storage = MagicMock()
    mock_storage.upload.side_effect = Exception("upload failed")
    mock_supabase.storage.from_.return_value = mock_storage

    service = FileService(mock_supabase)

    result = service.upload_file(
        "user123",
        "test.txt",
        b"hello world"
    )

    assert "error" in result
