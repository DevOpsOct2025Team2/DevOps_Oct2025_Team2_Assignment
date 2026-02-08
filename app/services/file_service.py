import logging
from datetime import datetime, timezone
from app.services.supabase_client import get_supabase_client

logger = logging.getLogger(__name__)

ALLOWED_SORT_FIELDS = {'created_at', 'filename', 'file_size'}

class FileService:
    def __init__(self, supabase_client=None):
        self.supabase = supabase_client or get_supabase_client()
    
    def get_user_files(self, user_id, page=1, per_page=10, sort_by='created_at', sort_order='desc'):
        try:
            if not user_id or not isinstance(user_id, str):
                return {'files': [], 'error': 'Invalid user ID'}
            
            if page < 1 or per_page < 1 or per_page > 100:
                return {'files': [], 'error': 'Invalid pagination parameters'}
            
            if sort_by not in ALLOWED_SORT_FIELDS:
                sort_by = 'created_at'

            if sort_order not in ('asc', 'desc'):
                sort_order = 'desc'

            query = self.supabase.table('files').select('*', count='exact')
            query = query.eq('owner_id', user_id)
            query = query.order(sort_by, desc=(sort_order == 'desc'))

            start = (page - 1) * per_page
            end = start + per_page - 1
            query = query.range(start, end)

            response = query.execute()

            files = []
            if response.data:
                for file in response.data:
                    files.append({
                        'id': file.get('id'),
                        'filename': file.get('filename'),
                        'file_size': file.get('file_size', 0),
                        'file_type': file.get('file_type'),
                        'created_at': file.get('created_at'),
                    })
            
            return {
                'files': files,
                'page': page,
                'per_page': per_page,
                'total': response.count or 0,
            }
        except Exception:
            logger.exception("Error retrieving user files")
            return {'files': [], 'error': 'Failed to retrieve files'}
    
    def delete_file(self, user_id, file_id):
        try:
            if not user_id or not isinstance(user_id, str):
                return {'error': 'Invalid user ID'}
            
            if not file_id or not isinstance(file_id, str):
                return {'error': 'Invalid file ID'}
            
            # verify file belongs to user
            try:
                file_check = self.supabase.table('files').select('id', 'owner_id').eq('id', file_id).single().execute()
            except Exception:
                logger.debug("Error checking file ownership")
                return {'error': 'File not found'}
            
            if not file_check or not file_check.data:
                return {'error': 'File not found'}
            
            # extract file data (handle both dict and list responses)
            file_data = file_check.data
            if isinstance(file_data, list) and len(file_data) > 0:
                file_data = file_data[0]
            elif not isinstance(file_data, dict):
                return {'error': 'File not found'}
            
            if file_data.get('owner_id') != user_id:
                logger.warning("Unauthorized delete attempt file_id=%s user_id=%s", file_id, user_id)
                return {'error': 'Unauthorized'}
            
            self.supabase.table('files').delete().eq('id', file_id).execute()
            return {'success': True, 'message': 'File deleted successfully'}
        except Exception:
            logger.exception("Error deleting file")
            return {'error': 'Failed to delete file'}
    
    def upload_file(self, user_id, filename, file_data, file_type='application/octet-stream', username=None):
        try:
            if not user_id or not isinstance(user_id, str):
                return {'error': 'Invalid user ID'}
            
            if not filename or not isinstance(filename, str):
                return {'error': 'Invalid filename'}
            if file_data is None:
                return {'error': 'Missing file data'}
            # normalize file_data to bytes
            if hasattr(file_data, 'read'):
                file_bytes = file_data.read()
            else:
                file_bytes = file_data
            if isinstance(file_bytes, memoryview):
                file_bytes = file_bytes.tobytes()
            if not isinstance(file_bytes, (bytes, bytearray)):
                return {'error': 'Invalid file data'}
            
            file_size = len(file_bytes)
            
            if file_size == 0:
                return {'error': 'File is empty'}
            
            if file_size > 50 * 1024 * 1024:
                return {'error': 'File size exceeds limit'}
            
            file_size = len(file_data)
            
            # store file metadata in db
            db_response = self.supabase.table('files').insert({
                'owner_id': user_id,
                'filename': filename,
                'file_size': file_size,
                'file_type': file_type,
            }).execute()
            
            if db_response.data:
                return {
                    'id': db_response.data[0].get('id'),
                    'filename': filename,
                    'file_size': file_size,
                    'file_type': file_type
                }
            return {'error': 'Failed to save file metadata'}
        except Exception:
            logger.exception("Error uploading file")
            return {'error': 'Failed to upload file'}