// prevent XSS
function escapeHtml(text) {
  const map = {
    '&': '&amp;',
    '<': '&lt;',
    '>': '&gt;',
    '"': '&quot;',
    "'": '&#039;'
  };
  return String(text).replace(/[&<>"']/g, m => map[m]);
}

document.addEventListener("DOMContentLoaded", () => {
  const usersBody = document.getElementById("users-body");
  const prevBtn = document.getElementById("prevBtn");
  const nextBtn = document.getElementById("nextBtn");
  const pageInfo = document.getElementById("pageInfo");
  const logoutBtn = document.getElementById("logoutBtn");

  // Filters
  const searchInput = document.getElementById("searchInput");
  const sortBy = document.getElementById("sortBy");
  const sortOrder = document.getElementById("sortOrder");
  const applyFilters = document.getElementById("applyFilters");

  let currentPage = 1;
  const perPage = 10;

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
    } catch (error) {
      console.error("Error:", error);
      usersBody.innerHTML = `<tr><td colspan="5" class="error">Error loading users: ${escapeHtml(error.message)}</td></tr>`;
    }
  }

  function renderUsers(users) {
    usersBody.innerHTML = "";
    if (!users || users.length === 0) {
      usersBody.innerHTML = '<tr><td colspan="5">No users found</td></tr>';
      return;
    }

    users.forEach((user) => {
      const row = document.createElement("tr");
      const cells = [
        escapeHtml(String(user.id || '')),
        escapeHtml(user.username || user.email || 'N/A'),
        escapeHtml(user.role || 'N/A'),
        escapeHtml(new Date(user.created_at).toLocaleString()),
        user.is_active ? 'Active' : 'Inactive'
      ];
      row.innerHTML = cells.map(cell => `<td>${cell}</td>`).join('');
      usersBody.appendChild(row);
    });
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

  // Initial load
  fetchUsers(currentPage);
});