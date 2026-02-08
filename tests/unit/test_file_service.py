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