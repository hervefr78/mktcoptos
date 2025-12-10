import React, { useState } from 'react';

/**
 * ShareDialog provides a simple interface for granting permissions on a node.
 * Permissions are represented by three checkboxes: view, edit and share.
 */
const ShareDialog = ({ isOpen, onClose, targetName, onShare }) => {
  const [permissions, setPermissions] = useState({
    view: true,
    edit: false,
    share: false,
  });

  if (!isOpen) return null;

  const toggle = (name) => {
    setPermissions((p) => ({ ...p, [name]: !p[name] }));
  };

  const handleSubmit = (e) => {
    e.preventDefault();
    onShare(permissions);
  };

  return (
    <div className="modal-backdrop">
      <div className="modal">
        <h2>Share {targetName}</h2>
        <form onSubmit={handleSubmit}>
          <label>
            <input
              type="checkbox"
              checked={permissions.view}
              onChange={() => toggle('view')}
            />
            View
          </label>
          <label>
            <input
              type="checkbox"
              checked={permissions.edit}
              onChange={() => toggle('edit')}
            />
            Edit
          </label>
          <label>
            <input
              type="checkbox"
              checked={permissions.share}
              onChange={() => toggle('share')}
            />
            Share
          </label>
          <div className="actions">
            <button type="submit">Save</button>
            <button type="button" onClick={onClose}>
              Cancel
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};

export default ShareDialog;
