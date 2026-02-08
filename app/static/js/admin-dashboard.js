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

async function loadUsers(page) {
    currentPage = page;
    const searchUsername = document.getElementById('searchUsername').value.trim();
    const sortBy = document.getElementById('sortBy').value;
    const sortOrder = document.getElementById('sortOrder').value;
    const perPage = parseInt(document.getElementById('perPage').value, 10);

    if (isNaN(page) || isNaN(perPage) || page < 1 || perPage < 1) {
        showMessage('Invalid pagination parameters', 'error');
        return;
    }

    try {
        const params = new URLSearchParams({
            page: String(page),
            per_page: String(perPage),
            sort_by: String(sortBy),
            order: String(sortOrder)
        });

        if (searchUsername) {
            params.append('search', searchUsername);
        }

        const response = await fetch(`/api/v1/admin/users?${params.toString()}`, {
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
            showMessage(data.message || data.error || 'Failed to load users', 'error');
            return;
        }

        renderUsers(data);
        renderPagination(data, perPage);
    } catch (error) {
        console.error('Error loading users:', error);
        showMessage('Error loading users', 'error');
    }
}

function renderUsers(data) {
    const tbody = document.getElementById('usersTableBody');

    if (!data || !data.users || data.users.length === 0) {
        tbody.innerHTML = '<tr><td colspan="5" class="no-files">No users found</td></tr>';
        return;
    }

    tbody.innerHTML = '';
    data.users.forEach(user => {
        const row = document.createElement('tr');

        const usernameCell = document.createElement('td');
        usernameCell.textContent = String(user.username || '');
        row.appendChild(usernameCell);

        const roleCell = document.createElement('td');
        roleCell.textContent = String(user.role || '');
        row.appendChild(roleCell);

        const statusCell = document.createElement('td');
        statusCell.textContent = user.is_active ? 'Active' : 'Inactive';
        row.appendChild(statusCell);

        const dateCell = document.createElement('td');
        dateCell.textContent = formatDate(String(user.created_at || ''));
        row.appendChild(dateCell);

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
        html += `<button onclick="loadUsers(${currentPage - 1})">← Previous</button>`;
    }

    html += `<span>Page ${currentPage} of ${totalPages}</span>`;

    if (currentPage < totalPages) {
        html += `<button onclick="loadUsers(${currentPage + 1})">Next →</button>`;
    }

    pagination.innerHTML = html;
}

function showCreateUserModal() {
    document.getElementById('create-user-modal').classList.remove('hidden');
}

function closeCreateUserModal() {
    document.getElementById('create-user-modal').classList.add('hidden');
    document.getElementById('create-user-form').reset();
    document.getElementById('create-user-error').textContent = '';
}

async function handleCreateUser(event) {
    event.preventDefault();

    const username = document.getElementById('new-username').value.trim();
    const password = document.getElementById('new-password').value;
    const role = document.getElementById('new-role').value;

    if (!username || username.length < 3 || username.length > 32) {
        showError('Username must be 3-32 characters');
        return;
    }

    if (!password || password.length < 8) {
        showError('Password must be at least 8 characters');
        return;
    }

    if (!['regular', 'admin'].includes(role)) {
        showError('Invalid role selected');
        return;
    }

    try {
        const response = await fetch('/api/v1/auth/users', {
            method: 'POST',
            credentials: 'include',
            headers: getAuthHeaders(),
            body: JSON.stringify({
                username: username,
                password: password,
                role: role
            })
        });

        const data = await response.json();

        if (response.ok) {
            showMessage('User created successfully', 'success');
            closeCreateUserModal();
            loadUsers(1);
        } else {
            showError(data.error || 'Failed to create user');
        }
    } catch (error) {
        console.error('Error creating user:', error);
        showError('Error creating user');
    }
}

function showError(message) {
    const errorDiv = document.getElementById('create-user-error');
    errorDiv.textContent = String(message);
    errorDiv.style.display = 'block';
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
    loadUsers(1);
});