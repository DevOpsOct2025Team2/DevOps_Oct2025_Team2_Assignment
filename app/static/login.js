const form = document.getElementById("login-form");
const errorEl = document.getElementById("error");
const statusEl = document.getElementById("status");
const nextPath = document.getElementById("nextPath").value || "";

const setStatus = (message) => {
  statusEl.textContent = message;
};

const setError = (message) => {
  errorEl.textContent = message;
};

form.addEventListener("submit", async (event) => {
  event.preventDefault();
  setError("");
  setStatus("Signing you in...");
  
  // Clear any existing token
  localStorage.removeItem("access_token");

  const formData = new FormData(form);
  const payload = {
    username: formData.get("username"),
    password: formData.get("password"),
  };

  try {
    const response = await fetch("/api/v1/auth/login", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      credentials: "same-origin",
      body: JSON.stringify(payload),
    });

    const data = await response.json();
    if (!response.ok) {
      throw new Error(data.message || "Login failed.");
    }

    // Store the token
    if (data.access_token) {
      localStorage.setItem("access_token", data.access_token);
    }

    const redirectTo =
      nextPath && nextPath.startsWith("/")
        ? nextPath
        : data.redirect_to || "/dashboard";
    setStatus("Redirecting...");
    window.location.assign(redirectTo);
  } catch (error) {
    setStatus("");
    setError(error.message);
  }
});
