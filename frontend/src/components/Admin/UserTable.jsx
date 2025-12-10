import React, { useEffect, useState } from 'react';

const emptyPermissions = { create: false, edit: false, delete: false };

const UserTable = () => {
  const [users, setUsers] = useState([]);
  const [newUser, setNewUser] = useState({ username: '', role: 'Viewer', permissions: { ...emptyPermissions } });
  const [editingUser, setEditingUser] = useState(null);

  const fetchUsers = async () => {
    try {
      const res = await fetch('/api/users');
      if (res.ok) {
        const data = await res.json();
        setUsers(data);
      }
    } catch (err) {
      console.error('Failed to fetch users', err);
    }
  };

  useEffect(() => {
    fetchUsers();
  }, []);

  const handleCreate = async () => {
    try {
      await fetch('/api/users', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(newUser)
      });
      setNewUser({ username: '', role: 'Viewer', permissions: { ...emptyPermissions } });
      fetchUsers();
    } catch (err) {
      console.error('Create user failed', err);
    }
  };

  const startEdit = (user) => {
    setEditingUser(JSON.parse(JSON.stringify(user)));
  };

  const cancelEdit = () => setEditingUser(null);

  const saveEdit = async () => {
    try {
      await fetch(`/api/users/${editingUser.id}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(editingUser)
      });
      setEditingUser(null);
      fetchUsers();
    } catch (err) {
      console.error('Update user failed', err);
    }
  };

  const handleDelete = async (id) => {
    try {
      await fetch(`/api/users/${id}`, { method: 'DELETE' });
      fetchUsers();
    } catch (err) {
      console.error('Delete user failed', err);
    }
  };

  const renderPermissions = (user, onChange, disabled = false) => (
    <>
      {['create', 'edit', 'delete'].map((perm) => (
        <label key={perm} style={{ marginRight: '8px' }}>
          <input
            type="checkbox"
            checked={user.permissions[perm]}
            disabled={disabled}
            onChange={(e) =>
              onChange({
                ...user,
                permissions: { ...user.permissions, [perm]: e.target.checked }
              })
            }
          />
          {perm}
        </label>
      ))}
    </>
  );

  return (
    <div>
      <h3>Users</h3>
      <table border="1" cellPadding="4" cellSpacing="0">
        <thead>
          <tr>
            <th>Username</th>
            <th>Role</th>
            <th>Permissions</th>
            <th>Actions</th>
          </tr>
        </thead>
        <tbody>
          {users.map((user) => (
            <tr key={user.id}>
              <td>
                {editingUser && editingUser.id === user.id ? (
                  <input
                    value={editingUser.username}
                    onChange={(e) => setEditingUser({ ...editingUser, username: e.target.value })}
                  />
                ) : (
                  user.username
                )}
              </td>
              <td>
                {editingUser && editingUser.id === user.id ? (
                  <select
                    value={editingUser.role}
                    onChange={(e) => setEditingUser({ ...editingUser, role: e.target.value })}
                  >
                    <option>Admin</option>
                    <option>Editor</option>
                    <option>Viewer</option>
                  </select>
                ) : (
                  user.role
                )}
              </td>
              <td>
                {editingUser && editingUser.id === user.id
                  ? renderPermissions(editingUser, setEditingUser)
                  : renderPermissions(user, () => {}, true)}
              </td>
              <td>
                {editingUser && editingUser.id === user.id ? (
                  <>
                    <button type="button" onClick={saveEdit} style={{ marginRight: '4px' }}>
                      Save
                    </button>
                    <button type="button" onClick={cancelEdit}>
                      Cancel
                    </button>
                  </>
                ) : (
                  <>
                    <button type="button" onClick={() => startEdit(user)} style={{ marginRight: '4px' }}>
                      Edit
                    </button>
                    <button type="button" onClick={() => handleDelete(user.id)}>
                      Delete
                    </button>
                  </>
                )}
              </td>
            </tr>
          ))}
          <tr>
            <td>
              <input
                value={newUser.username}
                onChange={(e) => setNewUser({ ...newUser, username: e.target.value })}
                placeholder="New username"
              />
            </td>
            <td>
              <select
                value={newUser.role}
                onChange={(e) => setNewUser({ ...newUser, role: e.target.value })}
              >
                <option>Admin</option>
                <option>Editor</option>
                <option>Viewer</option>
              </select>
            </td>
            <td>{renderPermissions(newUser, setNewUser)}</td>
            <td>
              <button type="button" onClick={handleCreate}>
                Add
              </button>
            </td>
          </tr>
        </tbody>
      </table>
    </div>
  );
};

export default UserTable;
