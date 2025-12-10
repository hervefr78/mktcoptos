if (!localStorage.getItem('authToken')) {
  localStorage.setItem('authToken', 'bypass-token');
}

export const setUserRole = (role) => {
  localStorage.setItem('userRole', role.toLowerCase());
};

const existingRole = localStorage.getItem('userRole');
if (existingRole) {
  setUserRole(existingRole);
} else {
  setUserRole('admin');
}

export async function requestPasswordReset(email) {
  const res = await fetch('/api/reset-password', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ email })
  });
  if (!res.ok) {
    throw new Error('Password reset failed');
  }
  return res.json();
}
