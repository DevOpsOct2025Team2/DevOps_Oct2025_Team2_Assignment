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

  // Check authentication & Role
  const token = localStorage.getItem("access_token"); 
  if (!token) {
    window.location.href = "/login"; 
    return;
  }

  // Parse token to check role immediately
  try {
      const payload = JSON.parse(atob(token.split('.')[1]));
      const userRole = payload.role || (payload.app_metadata && payload.app_metadata.role);
      
      if (userRole !== 'admin') {
          alert('Access denied: Admins only.');
          window.location.href = "/";
          return;
      }
  } catch (e) {
      console.error("Invalid token format", e);
      localStorage.removeItem("access_token");
      window.location.href = "/login";
      return;
  }

  // Logout handler
  logoutBtn.addEventListener("click", async () => {
    localStorage.removeItem("access_token");
    window.location.href = "/login";
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
          headers: {
            Authorization: `Bearer ${token}`,
          },
        },
      );

      if (response.status === 401 || response.status === 403) {
        localStorage.removeItem("access_token");
        alert(`Unauthorized access (${response.status}). Redirecting to login.`);
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
      fetchUsers(1); // Reset to page 1 on filter change
  });

  // Initial load
  fetchUsers(currentPage);
});