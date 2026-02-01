// rate limits, added localStorage persistence
const createUserRateLimit = {
  storageKey: 'createUserAttempts',
  maxAttempts: 3,
  windowMs: 300000, // 5 mins
  
  getAttempts() {
    try {
      const stored = localStorage.getItem(this.storageKey);
      return stored ? JSON.parse(stored) : [];
    } catch (e) {
      console.error('Error parsing rate limit data:', e);
      return [];
    }
  },
  
  setAttempts(attempts) {
    try {
      localStorage.setItem(this.storageKey, JSON.stringify(attempts));
    } catch (e) {
      console.error('Error storing rate limit data:', e);
    }
  },
  
  isLimited() {
    const now = Date.now();
    let attempts = this.getAttempts().filter(time => now - time < this.windowMs);
    this.setAttempts(attempts);
    return attempts.length >= this.maxAttempts;
  },
  
  recordAttempt() {
    const attempts = this.getAttempts();
    attempts.push(Date.now());
    this.setAttempts(attempts);
  },
  
  getRemainingTime() {
    const attempts = this.getAttempts();
    if (attempts.length === 0) return 0;
    const oldestAttempt = Math.min(...attempts);
    const now = Date.now();
    const elapsed = now - oldestAttempt;
    return Math.max(0, this.windowMs - elapsed);
  }
};
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
    let role = form.role.value.trim().toLowerCase();
    const error = document.getElementById('create-user-error');

    setSafeErrorText(error, '');
    // first check rate limits
    if (createUserRateLimit.isLimited()) {
      const remainingMs = createUserRateLimit.getRemainingTime();
      const remainingSeconds = Math.ceil(remainingMs / 1000);
      setSafeErrorText(error, `Too many attempts. Please wait ${remainingSeconds}s before trying again.`);
      return;
    }

    // Validate username length
    if (username.length < 3 || username.length > 32) {
      setSafeErrorText(error, 'Username must be 3-32 characters.');
      createUserRateLimit.recordAttempt();
      return;
    }
    
    // validate username (alphanumeric + underscore)
    const usernameRegex = /^[a-zA-Z0-9_]+$/;
    if (!usernameRegex.test(username)) {
      setSafeErrorText(error, 'Username can only contain letters, numbers, and underscores.');
      createUserRateLimit.recordAttempt();
      return;
    }

    // validate password strength
    const passwordRegex = /^(?=.*[A-Za-z])(?=.*\d)[A-Za-z\d@$!%*#?&]{8,}$/;
    if (!passwordRegex.test(password)) {
      setSafeErrorText(error, 'Password must be at least 8 characters with letters and numbers.');
      createUserRateLimit.recordAttempt();
      return;
    }

    // validate role
    if (role !== 'regular' && role !== 'admin') {
      setSafeErrorText(error, 'Invalid role selected.');
      createUserRateLimit.recordAttempt();
      return;
    }

    // backend receives with auth token via httponly cookie
    try {
      const resp = await fetch('/api/v1/users', {
        method: 'POST',
        headers: { 
          'Content-Type': 'application/json'
        },
        credentials: 'include',
        body: JSON.stringify({ username, password, role })
      });
      let data;
      try {
        data = await resp.json();
      } catch (parseError) {
        console.error('Failed to parse response:', parseError);
        setSafeErrorText(error, 'Server error. Please try again.');
        createUserRateLimit.recordAttempt();
        return;
      }

      if (resp.ok) {
        createUserRateLimit.recordAttempt();
        closeCreateUserModal();
        window.location.reload();
      } else {
        const errorMsg = data.error || data.message || 'Failed to create user.';
        setSafeErrorText(error, errorMsg);
        createUserRateLimit.recordAttempt();
      }
    } catch (err) {
      console.error('Create user error:', err);
      setSafeErrorText(error, 'Network error. Please try again.');
      createUserRateLimit.recordAttempt();
    }
  });

  // modal triggers button
  const createUserBtn = document.getElementById('createUserBtn');
  if (createUserBtn) {
    createUserBtn.addEventListener('click', showCreateUserModal);
  }
});