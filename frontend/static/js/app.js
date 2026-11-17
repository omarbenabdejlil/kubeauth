const API = "/api/v1";

async function loadAll() {
  await Promise.all([loadHealth(), loadBindings(), loadUsers(), loadNamespaces()]);
}

async function loadHealth() {
  try {
    const res = await fetch(`${API}/health`);
    const data = await res.json();
    const alertBox = document.getElementById("statusAlert");
    if (!data.k8s_connected) {
      alertBox.className = "alert alert-warning";
      alertBox.innerHTML = `<strong>Notice:</strong> No active Kubernetes cluster detected. Operating in mock mode. Keycloak is ready.`;
      alertBox.classList.remove("d-none");
    } else {
      alertBox.className = "alert alert-success";
      alertBox.innerHTML = `Connected to Kubernetes Cluster & Keycloak Realm: <strong>${data.realm}</strong>`;
      alertBox.classList.remove("d-none");
    }
  } catch (err) {
    console.error("Health check error:", err);
  }
}

async function loadBindings() {
  const tbody = document.getElementById("bindingsTable");
  try {
    const res = await fetch(`${API}/bindings`);
    const data = await res.json();
    if (!data.length) {
      tbody.innerHTML = `<tr><td colspan="5" class="text-center py-4 text-muted">No RoleBindings created yet. Click "Assign Developer Access" to add one.</td></tr>`;
      return;
    }
    tbody.innerHTML = data.map(b => `
      <tr>
        <td class="ps-4"><code>${b.name}</code></td>
        <td><i class="bi bi-person-fill text-secondary me-1"></i> <strong>${b.subject}</strong></td>
        <td><span class="badge bg-secondary">${b.namespace}</span></td>
        <td><span class="badge bg-primary px-2 py-1">${b.role}</span></td>
        <td class="text-end pe-4">
          <button class="btn btn-sm btn-outline-danger" onclick="deleteBinding('${b.namespace}', '${b.name}')">
            <i class="bi bi-trash"></i> Revoke
          </button>
        </td>
      </tr>
    `).join("");
  } catch (e) {
    tbody.innerHTML = `<tr><td colspan="5" class="text-danger ps-4">Failed to load bindings: ${e.message}</td></tr>`;
  }
}

async function loadUsers() {
  try {
    const res = await fetch(`${API}/users`);
    const users = await res.json();
    const select = document.getElementById("userSelect");
    select.innerHTML = users.map(u =>
      `<option value="${u.username}">${u.username} (${u.firstName} ${u.lastName} - ${u.email})</option>`
    ).join("");
  } catch (e) {
    console.error("Failed to load users:", e);
  }
}

async function loadNamespaces() {
  try {
    const res = await fetch(`${API}/namespaces`);
    const namespaces = await res.json();
    const select = document.getElementById("namespaceSelect");
    select.innerHTML = namespaces.map(ns => `<option value="${ns}">${ns}</option>`).join("");
  } catch (e) {
    console.error("Failed to load namespaces:", e);
  }
}

document.getElementById("assignForm").addEventListener("submit", async (e) => {
  e.preventDefault();
  const btn = document.getElementById("btnSubmit");
  btn.disabled = true;

  const payload = {
    username: document.getElementById("userSelect").value,
    namespace: document.getElementById("namespaceSelect").value,
    role: document.getElementById("roleSelect").value
  };

  try {
    const res = await fetch(`${API}/bindings`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload)
    });
    const result = await res.json();
    if (!res.ok) throw new Error(result.detail || "Error creating binding");

    bootstrap.Modal.getInstance(document.getElementById("assignModal")).hide();
    loadBindings();
  } catch (err) {
    alert(err.message);
  } finally {
    btn.disabled = false;
  }
});

async function deleteBinding(namespace, name) {
  if (!confirm(`Are you sure you want to revoke binding "${name}" in namespace "${namespace}"?`)) return;
  try {
    const res = await fetch(`${API}/bindings/${namespace}/${name}`, { method: "DELETE" });
    if (!res.ok) throw new Error("Delete failed");
    loadBindings();
  } catch (err) {
    alert(err.message);
  }
}

document.addEventListener("DOMContentLoaded", loadAll);
