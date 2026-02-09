let currentPage = 1;

function getAuthToken() {
    const cookies = document.cookie.split(';');
    for (let cookie of cookies) {
        const [name, value] = cookie.trim().split('=');
        if (name === 'access_token') {
            return decodeURIComponent(value);
        }
    }
    return null;
}

function getAuthHeaders() {
    const token = getAuthToken();
    if (!token) {
        return { 'Content-Type': 'application/json' };
    }
    return {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${token}`
    };
}

function initUserInfo() {
    const userRole = document.getElementById('userRole');
    if (userRole && userRole.textContent) {
        return;
    }
}

async function loadFiles(page) {
    currentPage = page;
    const sortBy = document.getElementById('sortBy').value;
    const sortOrder = document.getElementById('sortOrder').value;
    const perPage = parseInt(document.getElementById('perPage').value, 10);

    if (isNaN(page) || isNaN(perPage) || page < 1 || perPage < 1 || perPage > 100) {
        showMessage('Invalid pagination parameters', 'error');
        return;
    }

    if (!['created_at', 'filename', 'file_size'].includes(sortBy)) {
        showMessage('Invalid sort parameter', 'error');
        return;
    }
    if (!['asc', 'desc'].includes(sortOrder)) {
        showMessage('Invalid sort order', 'error');
        return;
    }

    try {
        const params = new URLSearchParams({
            page: String(page),
            per_page: String(perPage),
            sort_by: String(sortBy),
            order: String(sortOrder)
        });

        const response = await fetch(`/api/v1/files/me?${params.toString()}`, {
            method: 'GET',
            credentials: 'include',
            headers: getAuthHeaders()
        });

        if (response.status === 401 || response.status === 403) {
            window.location.href = '/login';
            return;
        }

        const data = await response.json();

        if (!response.ok) {
            showMessage(data.message || data.error || 'Failed to load files', 'error');
            return;
        }

        renderFiles(data);
        renderPagination(data, perPage);
    } catch (error) {
        console.error('Error loading files:', error);
        showMessage('Error loading files', 'error');
    }
}


function showUploadModal() {
    document.getElementById('upload-modal').classList.remove('hidden');
    document.getElementById('upload-form').reset();
    document.getElementById('upload-error').textContent = '';
    document.getElementById('upload-progress').classList.add('hidden');
}


function closeUploadModal() {
    document.getElementById('upload-modal').classList.add('hidden');
    document.getElementById('upload-form').reset();
    document.getElementById('upload-error').textContent = '';
}

async function handleFileUpload(event) {
    event.preventDefault();

    const fileInput = document.getElementById('file-input');
    const file = fileInput.files[0];
    const errorDiv = document.getElementById('upload-error');
    const progressDiv = document.getElementById('upload-progress');

    if (!file) {
        showError('Please select a file', errorDiv);
        return;
    }

    const MAX_FILE_SIZE = 50 * 1024 * 1024; // 50MB
    if (file.size > MAX_FILE_SIZE) {
        showError('File size exceeds 50MB limit', errorDiv);
        return;
    }

    const ALLOWED_TYPES = {
        'application/pdf': '.pdf',
        'application/msword': '.doc',
        'application/vnd.openxmlformats-officedocument.wordprocessingml.document': '.docx',
        'text/plain': '.txt',
        'application/vnd.ms-excel': '.xls',
        'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet': '.xlsx',
        'image/jpeg': '.jpg,.jpeg',
        'image/png': '.png',
        'application/zip': '.zip',
        'application/x-zip-compressed': '.zip'
    };

    if (!ALLOWED_TYPES[file.type]) {
        showError('File type not allowed. Allowed types: PDF, DOC, DOCX, TXT, XLS, XLSX, JPG, PNG, ZIP', errorDiv);
        return;
    }

    if (!file.name || file.name.length > 255) {
        showError('Invalid filename', errorDiv);
        return;
    }

    try {
        const formData = new FormData();
        formData.append('file', file);

        progressDiv.classList.remove('hidden');

        const xhr = new XMLHttpRequest();
        xhr.withCredentials = true;

        // track upload progress
        xhr.upload.addEventListener('progress', (event) => {
            if (event.lengthComputable) {
                const percentComplete = Math.round((event.loaded / event.total) * 100);
                document.getElementById('progressFill').style.width = percentComplete + '%';
                document.getElementById('progressText').textContent = `Uploading... ${percentComplete}%`;
            }
        });

        xhr.addEventListener('load', () => {
            if (xhr.status === 200 || xhr.status === 201) {
                const response = JSON.parse(xhr.responseText);
                showMessage('File uploaded successfully', 'success');
                closeUploadModal();
                loadFiles(1);
            } else {
                const response = JSON.parse(xhr.responseText);
                showError(response.error || 'Upload failed', errorDiv);
            }
            progressDiv.classList.add('hidden');
        });

        xhr.addEventListener('error', () => {
            showError('Upload failed', errorDiv);
            progressDiv.classList.add('hidden');
        });

        xhr.open('POST', '/api/v1/files/upload');
        xhr.send(formData);

    } catch (error) {
        console.error('Error uploading file:', error);
        showError('Upload error', errorDiv);
        progressDiv.classList.add('hidden');
    }
}

function showError(message, errorDiv) {
    errorDiv.textContent = String(message);
    errorDiv.style.display = 'block';
}

function renderFiles(data) {
    const tbody = document.getElementById('filesTableBody');

    if (!data || !data.files || data.files.length === 0) {
        tbody.innerHTML = '<tr><td colspan="5" class="no-files">No files uploaded yet</td></tr>';
        return;
    }

    tbody.innerHTML = '';
    data.files.forEach(file => {
        const fileId = String(file.id || '');
        const filename = String(file.filename || '');
        const fileType = String(file.file_type || 'Unknown');
        const fileSize = Number(file.file_size || 0);
        const createdAt = String(file.created_at || '');

        const row = document.createElement('tr');

        const nameCell = document.createElement('td');
        nameCell.textContent = filename;
        row.appendChild(nameCell);

        const sizeCell = document.createElement('td');
        sizeCell.textContent = (fileSize / 1024).toFixed(2);
        row.appendChild(sizeCell);

        const typeCell = document.createElement('td');
        typeCell.textContent = fileType;
        row.appendChild(typeCell);

        const dateCell = document.createElement('td');
        dateCell.textContent = formatDate(createdAt);
        row.appendChild(dateCell);

        const actionCell = document.createElement('td');

        const downloadBtn = document.createElement('button');
        downloadBtn.className = 'btn btn-download';
        downloadBtn.textContent = 'Download';
        downloadBtn.onclick = () => downloadFile(encodeURIComponent(fileId), filename);
        actionCell.appendChild(downloadBtn);

        const deleteBtn = document.createElement('button');
        deleteBtn.className = 'delete-btn';
        deleteBtn.textContent = 'Delete';
        deleteBtn.onclick = () => deleteFile(encodeURIComponent(fileId));
        actionCell.appendChild(deleteBtn);
        row.appendChild(actionCell);

        tbody.appendChild(row);
    });
}

function renderPagination(data, perPage) {
    const pagination = document.getElementById('pagination');
    const totalPages = Math.ceil((data.total || 0) / perPage);

    if (totalPages <= 1) {
        pagination.innerHTML = '';
        return;
    }

    let html = '';
    if (currentPage > 1) {
        html += `<button onclick="loadFiles(${currentPage - 1})">← Previous</button>`;
    }

    html += `<span>Page ${currentPage} of ${totalPages}</span>`;

    if (currentPage < totalPages) {
        html += `<button onclick="loadFiles(${currentPage + 1})">Next →</button>`;
    }

    pagination.innerHTML = html;
}

async function downloadFile(fileId, filename) {
    if (!fileId || typeof fileId !== 'string') {
        showMessage('Invalid file ID', 'error');
        return;
    }

    try {
        const response = await fetch(`/api/v1/files/${encodeURIComponent(fileId)}/download`, {
            method: 'GET',
            credentials: 'include',
            headers: getAuthHeaders()
        });

        if (response.status === 401) {
            window.location.href = '/login';
            return;
        }

        if (response.status === 403) {
            const data = await response.json();
            showMessage(data.message || 'You do not have permission to download this file', 'error');
            return;
        }

        if (response.status === 404) {
            showMessage('File not found', 'error');
            return;
        }

        if (!response.ok) {
            let errorMsg = 'Failed to download file';
            try {
                const data = await response.json();
                errorMsg = data.message || data.error || errorMsg;
            } catch (e) {
                // response may not be JSON for unexpected errors
            }
            showMessage(errorMsg, 'error');
            return;
        }

        // Create a blob from the response and trigger browser download
        const blob = await response.blob();
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = filename || 'download';
        document.body.appendChild(a);
        a.click();
        a.remove();
        window.URL.revokeObjectURL(url);

        showMessage('File downloaded successfully', 'success');
    } catch (error) {
        console.error('Error downloading file:', error);
        showMessage('Error downloading file', 'error');
    }
}

async function deleteFile(fileId) {
    if (!fileId || typeof fileId !== 'string') {
        showMessage('Invalid file ID', 'error');
        return;
    }

    if (!confirm('Are you sure you want to delete this file? This action cannot be undone.')) {
        return;
    }

    try {
        const response = await fetch(`/api/v1/files/${encodeURIComponent(fileId)}`, {
            method: 'DELETE',
            credentials: 'include',
            headers: getAuthHeaders()
        });
        const data = await response.json();

        if (response.ok) {
            showMessage('File deleted successfully', 'success');
            loadFiles(1);
        } else {
            showMessage(data.error || 'Failed to delete file', 'error');
        }
    } catch (error) {
        console.error('Error deleting file:', error);
        showMessage('Error deleting file', 'error');
    }
}

function showMessage(message, type) {
    const messageDiv = document.getElementById('message');
    if (!messageDiv) return;

    messageDiv.className = `message ${type}`;
    messageDiv.textContent = String(message);

    if (type === 'success') {
        setTimeout(() => {
            messageDiv.className = 'message';
            messageDiv.textContent = '';
        }, 5000);
    }
}

function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

function escapeAttr(text) {
    if (typeof text !== 'string') return '';
    return text
        .replace(/&/g, '&amp;')
        .replace(/'/g, '&#39;')
        .replace(/"/g, '&quot;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;');
}

function formatDate(dateString) {
    if (!dateString || typeof dateString !== 'string') return '';

    try {
        const date = new Date(dateString);
        if (isNaN(date.getTime())) return dateString;

        return date.toLocaleDateString('en-US', {
            year: 'numeric',
            month: 'short',
            day: 'numeric'
        });
    } catch (error) {
        console.error('Date formatting error:', error);
        return dateString;
    }
}

function logout() {
    if (confirm('Are you sure you want to logout?')) {
        fetch('/api/v1/auth/logout', {
            method: 'POST',
            credentials: 'include',
            headers: getAuthHeaders()
        })
        .then(response => response.json())
        .then(data => {
            if (data.redirect_to && typeof data.redirect_to === 'string' && data.redirect_to.startsWith('/')) {
                window.location.href = data.redirect_to;
            } else {
                window.location.href = '/login';
            }
        })
        .catch(error => {
            console.error('Logout error:', error);
            window.location.href = '/login';
        });
    }
}

document.addEventListener('DOMContentLoaded', () => {
    initUserInfo();
    loadFiles(1);
});
