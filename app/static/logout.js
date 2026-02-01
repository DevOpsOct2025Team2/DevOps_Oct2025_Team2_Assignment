const logoutForm = document.getElementById("logout-form");
const logoutModal = document.getElementById("logout-modal");
let isSubmitting = false;

function showLogoutModal(event) {
  event.preventDefault();
  if (logoutModal) {
    logoutModal.classList.remove("hidden");
  }
}

function closeLogoutModal() {
  if (logoutModal) {
    logoutModal.classList.add("hidden");
  }
}

if (logoutForm) {
  logoutForm.addEventListener("submit", async (event) => {
    event.preventDefault();
    
    if (isSubmitting) {
      return;
    }

    isSubmitting = true;

    const submitButton = logoutForm.querySelector("button[type='submit']");
    if (submitButton) {
      submitButton.disabled = true;
      submitButton.textContent = "Logging out...";
    }

    try {
      const response = await fetch("/api/v1/auth/logout", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        credentials: "same-origin",
      });

      if (!response.ok) {
        throw new Error("Logout failed");
      }

      window.location.assign("/login");
    } catch (error) {
      isSubmitting = false;
      if (submitButton) {
        submitButton.disabled = false;
        submitButton.textContent = "Yes, Logout";
      }
      console.error("Logout error:", error);
    }
  });
}

if (logoutModal) {
  logoutModal.addEventListener("click", (event) => {
    if (event.target === logoutModal.querySelector(".modal-backdrop")) {
      closeLogoutModal();
    }
  });
}