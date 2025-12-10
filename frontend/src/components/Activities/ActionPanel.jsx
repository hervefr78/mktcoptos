import React, { useState } from 'react';
import {
  copyToClipboard,
  exportToWordpress,
  downloadContent,
  shareOnLinkedIn,
  shareOnX,
} from '../../utils/integrations';

export default function ActionPanel({ content = '' }) {
  const [toast, setToast] = useState('');

  const showToast = (msg) => {
    setToast(msg);
    setTimeout(() => setToast(''), 3000);
  };

  const handleCopy = () => {
    copyToClipboard(content)
      .then(() => showToast('Copied to clipboard'))
      .catch((e) => {
        console.error(e);
        showToast('Copy failed');
      });
  };

  const handleExport = async () => {
    try {
      await exportToWordpress(content);
      showToast('Exported to WordPress');
    } catch (e) {
      console.error(e);
      showToast('Failed to export to WordPress');
    }
  };

  const handleDownload = (format) => {
    try {
      downloadContent(format, content);
      showToast(`Downloaded ${format}`);
    } catch (e) {
      console.error(e);
      showToast(`Failed to download ${format}`);
    }
  };

  const handleShareLinkedIn = async () => {
    try {
      await shareOnLinkedIn(content);
      showToast('Shared on LinkedIn');
    } catch (e) {
      console.error(e);
      showToast('Failed to share on LinkedIn');
    }
  };

  const handleShareX = async () => {
    try {
      await shareOnX(content);
      showToast('Shared on X');
    } catch (e) {
      console.error(e);
      showToast('Failed to share on X');
    }
  };

  return (
    <div className="action-panel">
      <button onClick={handleCopy}>Copy</button>
      <button onClick={handleExport}>Export to WordPress</button>
      <div className="download-group">
        <span>Download:</span>
        <button onClick={() => handleDownload('pdf')}>PDF</button>
        <button onClick={() => handleDownload('html')}>HTML</button>
        <button onClick={() => handleDownload('markdown')}>Markdown</button>
      </div>
      <button onClick={handleShareLinkedIn}>Share on LinkedIn</button>
      <button onClick={handleShareX}>Share on X</button>
      {toast && <div className="toast">{toast}</div>}
    </div>
  );
}
