// prevent DOM-based XSS
function setSafeErrorText(element, text) {
  element.textContent = text;
}

function showCreateUserModal() {
  document.getElementById('create-user-modal').classList.remove('hidden');
}

function closeCreateUserModal() {
  const modal = document.getElementById('create-user-modal');
  const form = document.getElementById('create-user-form');
  const error = document.getElementById('create-user-error');
  
  modal.classList.add('hidden');
  form.reset();
  setSafeErrorText(error, '');
}

document.addEventListener('DOMContentLoaded', function () {
  const form = document.getElementById('create-user-form');
  if (!form) return;

  form.addEventListener('submit', async function (e) {
    e.preventDefault();
    const username = form.username.value.trim();
    const password = form.password.value;
    const role = form.role.value;
    const error = document.getElementById('create-user-error');

    setSafeErrorText(error, '');

    // Validate username length
    if (username.length < 3 || username.length > 32) {
      setSafeErrorText(error, 'Username must be 3-32 characters.');
      return;
    }
    
    // validate username (alphanumeric + underscore)
    const usernameRegex = /^[a-zA-Z0-9_]+$/;
    if (!usernameRegex.test(username)) {
      setSafeErrorText(error, 'Username can only contain letters, numbers, and underscores.');
      return;
    }

    // validate password strength
    const passwordRegex = /^(?=.*[A-Za-z])(?=.*\d)[A-Za-z\d@$!%*#?&]{8,}$/;
    if (!passwordRegex.test(password)) {
      setSafeErrorText(error, 'Password must be at least 8 characters with letters and numbers.');
      return;
    }

    // validate role
    if (role !== 'user' && role !== 'admin') {
      setSafeErrorText(error, 'Invalid role selected.');
      return;
    }

    // backend receives with auth token
    try {
      const token = sessionStorage.getItem('access_token') || localStorage.getItem('access_token');
      if (!token) {
        setSafeErrorText(error, 'Authentication required. Please log in again.');
        return;
      }

      const resp = await fetch('/api/v1/users', {
        method: 'POST',
        headers: { 
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`
        },
        credentials: 'include',
        body: JSON.stringify({ username, password, role })
      });
      const data = await resp.json();

      if (resp.ok) {
        closeCreateUserModal();
        window.location.reload();
      } else {
        const errorMsg = data.error || data.message || 'Failed to create user.';
        setSafeErrorText(error, errorMsg);
      }
    } catch (err) {
      console.error('Create user error:', err);
      setSafeErrorText(error, 'Network error. Please try again.');
    }
  });

  // modal triggers button
  const createUserBtn = document.getElementById('createUserBtn');
  if (createUserBtn) {
    createUserBtn.addEventListener('click', showCreateUserModal);
  }
});