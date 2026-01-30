function showCreateUserModal() {
  document.getElementById('create-user-modal').classList.remove('hidden');
}

function closeCreateUserModal() {
  const modal = document.getElementById('create-user-modal');
  const form = document.getElementById('create-user-form');
  const error = document.getElementById('create-user-error');
  
  modal.classList.add('hidden');
  form.reset();
  error.textContent = '';
}

// to validate frontend and AJAX submit so dont need to reload
document.addEventListener('DOMContentLoaded', function () {
  const form = document.getElementById('create-user-form');
  if (!form) return;

  form.addEventListener('submit', async function (e) {
    e.preventDefault();
    const username = form.username.value.trim();
    const password = form.password.value;
    const role = form.role.value;
    const error = document.getElementById('create-user-error');

    error.textContent = '';

    // validate username
    if (username.length < 3 || username.length > 32) {
      error.textContent = 'Username must be 3-32 characters.';
      return;
    }
    // validate password
    const passwordRegex = /^(?=.*[A-Za-z])(?=.*\d)[A-Za-z\d@$!%*#?&]{8,}$/;
    if (!passwordRegex.test(password)) {
      error.textContent = 'Password must be at least 8 characters with letters and numbers.';
      return;
    }
    // validate role
    if (role !== 'user' && role !== 'admin') {
      error.textContent = 'Invalid role selected.';
      return;
    }

    // backend receives
    try {
      const resp = await fetch('/api/users', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ username, password, role })
      });
      const data = await response.json();

      if (response.ok) {
        closeCreateUserModal();
        window.location.reload();
      } else {
        error.textContent = data.error || 'Failed to create user.';
      }
    } catch (err) {
      error.textContent = 'Network error. Please try again.';
    }
  });
});