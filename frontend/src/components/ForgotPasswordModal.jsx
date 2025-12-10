import React, { useState } from 'react';
import { requestPasswordReset } from '../utils/auth';

const ForgotPasswordModal = ({ isOpen, onClose }) => {
  const [email, setEmail] = useState('');
  const [status, setStatus] = useState(null);

  if (!isOpen) {
    return null;
  }

  const handleSubmit = async (e) => {
    e.preventDefault();
    setStatus(null);
    try {
      await requestPasswordReset(email);
      setStatus('success');
    } catch (err) {
      setStatus('error');
    }
  };

  return (
    <div className="modal-backdrop">
      <div className="modal">
        <h2>Reset Password</h2>
        {status === 'success' ? (
          <p>Check your email for reset instructions.</p>
        ) : (
          <form onSubmit={handleSubmit}>
            <input
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="Email"
              required
            />
            <button type="submit">Send Reset Link</button>
          </form>
        )}
        {status === 'error' && <p className="error">Failed to send reset link.</p>}
        <button type="button" onClick={onClose}>
          Close
        </button>
      </div>
    </div>
  );
};

export default ForgotPasswordModal;
