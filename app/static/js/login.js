document.addEventListener('DOMContentLoaded', () => {
    const loginForm = document.getElementById('login-form');
    if (loginForm) {
        loginForm.addEventListener('submit', handleLogin);
    }
});

async function handleLogin(event) {
    event.preventDefault();

    const username = document.getElementById('username').value.trim();
    const password = document.getElementById('password').value;
    const errorDiv = document.getElementById('error-message');

    if (errorDiv) {
        errorDiv.textContent = '';
        errorDiv.style.display = 'none';
    }

    if (!username || !password) {
        showError('Username and password are required', errorDiv);
        return;
    }

    try {
        const response = await fetch('/api/v1/auth/login', {
            method: 'POST',
            credentials: 'include',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                username: String(username),
                password: String(password)
            })
        });

        const data = await response.json();

        if (!response.ok) {
            showError(data.message || data.error || 'Login failed', errorDiv);
            return;
        }
        const redirectTo = data.redirect_to;
        if (!redirectTo || typeof redirectTo !== 'string') {
            showError('Invalid server response', errorDiv);
            return;
        }
        try {
            const url = new URL(redirectTo, window.location.origin);
            // redirect stays on same origin
            if (url.origin !== window.location.origin) {
                showError('Invalid server response', errorDiv);
                return;
            }
            window.location.href = url.pathname + url.search + url.hash;
        } catch {
            showError('Invalid server response', errorDiv);
            return;
        }
    } catch (error) {
        console.error('Login error:', error);
        showError('Network error. Please try again.', errorDiv);
    }
}

function showError(message, errorDiv) {
    if (!errorDiv) return;
    
    errorDiv.textContent = String(message);
    errorDiv.style.display = 'block';
    errorDiv.scrollIntoView({ behavior: 'smooth', block: 'center' });
}