// rate limiting for fetch reqs
const rateLimiter = {
  maxAttempts: 10,
  windowMs: 60000, // 1 min
  attempts: [],
  
  isLimited() {
    const now = Date.now();
    this.attempts = this.attempts.filter(time => now - time < this.windowMs);
    return this.attempts.length >= this.maxAttempts;
  },
  
  recordAttempt() {
    this.attempts.push(Date.now());
  }
};

// prevent XSS
function escapeHtml(text) {
  const div = document.createElement('div');
  div.textContent = text;
  return div.innerHTML;
}

document.addEventListener("DOMContentLoaded", () => {
  const usersBody = document.getElementById("users-body");
  const prevBtn = document.getElementById("prevBtn");
  const nextBtn = document.getElementById("nextBtn");
  const pageInfo = document.getElementById("pageInfo");
  const logoutBtn = document.getElementById("logoutBtn");
  const statusMessage = document.getElementById("status-message");
  const actionsHeader = document.getElementById("actions-header");

  // Filters
  const searchInput = document.getElementById("searchInput");
  const sortBy = document.getElementById("sortBy");
  const sortOrder = document.getElementById("sortOrder");
  const applyFilters = document.getElementById("applyFilters");
  const currentUserRole = (document.body.dataset.currentUserRole || "").toLowerCase();
  const currentUserId = (document.body.dataset.currentUserId || "").trim();
  const canDeleteUsers = currentUserRole === "admin";

  let currentPage = 1;
  const perPage = 10;

  if (canDeleteUsers && actionsHeader) {
    actionsHeader.classList.remove("hidden");
  }

  function getTableColspan() {
    return canDeleteUsers ? 6 : 5;
  }

  function showStatus(message, type) {
    if (!statusMessage) return;
    statusMessage.textContent = message;
    statusMessage.classList.remove("hidden", "status-success", "status-error");
    statusMessage.classList.add(type === "error" ? "status-error" : "status-success");
  }

  // Logout handler
  logoutBtn.addEventListener("click", async () => {
    try {
      await fetch("/api/v1/auth/logout", {
        method: "POST",
        credentials: "same-origin"
      });
    } finally {
      window.location.href = "/login";
    }
  });

  async function fetchUsers(page) {
    if (rateLimiter.isLimited()) {
      alert("Too many requests. Please wait a moment.");
      return;
    }
    rateLimiter.recordAttempt();
    
    const search = searchInput.value;
    const sort = sortBy.value;
    const order = sortOrder.value;

    try {
      const queryParams = new URLSearchParams({
          page: page,
          per_page: perPage,
          search: search,
          sort_by: sort,
          order: order
      });

      const response = await fetch(
        `/api/v1/admin/users?${queryParams.toString()}`,
        {
          credentials: "same-origin"
        }
      );

      if (response.status === 401 || response.status === 403) {
        window.location.href = "/login";
        return;
      }

      if (!response.ok) {
        throw new Error("Failed to fetch users");
      }

      const data = await response.json();
      renderUsers(data.users);
      updatePagination(data.page, data.total);
      currentPage = page;
      return data;
    } catch (error) {
      console.error("Error:", error);
      const errorRow = document.createElement('tr');
      const errorCell = document.createElement('td');
      errorCell.colSpan = '5';
      errorCell.className = 'error';
      errorCell.textContent = `Error loading users: ${String(error.message)}`;
      errorRow.appendChild(errorCell);
      usersBody.innerHTML = '';
      usersBody.appendChild(errorRow);
    }
  }

  function renderUsers(users) {
    usersBody.innerHTML = "";
    if (!users || users.length === 0) {
      usersBody.innerHTML = `<tr><td colspan="${getTableColspan()}">No users found</td></tr>`;
      return;
    }

    users.forEach((user) => {
      const row = document.createElement("tr");
      const username = user.username || user.email || "N/A";
      const cellData = [
        user.id || "",
        username,
        user.role || "N/A",
        user.created_at ? new Date(user.created_at).toLocaleString() : "N/A",
        user.is_active ? "Active" : "Inactive"
      ];

      cellData.forEach(cellText => {
        const td = document.createElement("td");
        td.textContent = escapeHtml(String(cellText));
        row.appendChild(td);
      });
      
      if (canDeleteUsers) {
        const isSelf = String(user.id || "").trim() === currentUserId;
        const safeUserId = escapeHtml(String(user.id || ""));
        const safeUsername = escapeHtml(String(username));

        const actionTd = document.createElement("td");
        const button = document.createElement("button");
        button.className = "btn btn-delete";
        button.disabled = isSelf;
        button.title = isSelf ? "You cannot delete your own account" : "Delete user";
        button.textContent = "Delete";

        if (!isSelf) {
          button.classList.add("delete-user-btn");
          button.dataset.userId = safeUserId;
          button.dataset.username = safeUsername;
        }

        actionTd.appendChild(button);
        row.appendChild(actionTd);
      }
      usersBody.appendChild(row);
    });
  }

  async function deleteUser(userId, username) {
    if (!canDeleteUsers) return;

    const confirmed = window.confirm(`Are you sure you want to delete user "${username}"?`);
    if (!confirmed) return;

    try {
      const response = await fetch(`/api/v1/admin/users/${encodeURIComponent(userId)}`, {
        method: "DELETE",
        credentials: "same-origin"
      });

      if (response.status === 401 || response.status === 403) {
        window.location.href = "/login";
        return;
      }

      const data = await response.json();
      if (!response.ok) {
        throw new Error(data.error || data.message || "Failed to delete user.");
      }

      showStatus(data.message || "User deleted successfully.", "success");

      const refreshed = await fetchUsers(currentPage);
      if (refreshed && refreshed.users && refreshed.users.length === 0 && currentPage > 1) {
        await fetchUsers(currentPage - 1);
      }
    } catch (error) {
      console.error("Delete user error:", error);
      showStatus(error.message || "Failed to delete user.", "error");
    }
  }

  function updatePagination(page, total) {
    pageInfo.textContent = `Page ${page}`;
    prevBtn.disabled = page <= 1;
    
    // total is total items
    const totalPages = Math.ceil(total / perPage);
    nextBtn.disabled = page >= totalPages;
  }

  prevBtn.addEventListener("click", () => {
    if (currentPage > 1) fetchUsers(currentPage - 1);
  });

  nextBtn.addEventListener("click", () => {
    fetchUsers(currentPage + 1);
  });
  
  applyFilters.addEventListener("click", () => {
      fetchUsers(1); // Reset to page 1 1 on filter change filter change
  });

  usersBody.addEventListener("click", (event) => {
    const button = event.target.closest(".delete-user-btn");
    if (!button) return;

    const userId = button.dataset.userId;
    const username = button.dataset.username || "this user";
    if (!userId) {
      showStatus("Invalid user id.", "error");
      return;
    }
    deleteUser(userId, username);
  });

  // Initial load
  fetchUsers(currentPage);
});
