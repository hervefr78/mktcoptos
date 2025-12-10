export async function copyToClipboard(text) {
  try {
    await navigator.clipboard.writeText(text);
  } catch (e) {
    console.error('Copy failed', e);
    throw e;
  }
}

export async function exportToWordpress(content) {
  const res = await fetch('/api/export/wordpress', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ content })
  });
  if (!res.ok) {
    throw new Error('WordPress export failed');
  }
  return res.json();
}

export function downloadContent(format, content) {
  let mime = 'text/plain';
  let extension = format;
  switch (format) {
    case 'pdf':
      mime = 'application/pdf';
      extension = 'pdf';
      break;
    case 'html':
      mime = 'text/html';
      extension = 'html';
      break;
    case 'markdown':
    case 'md':
      mime = 'text/markdown';
      extension = 'md';
      break;
    default:
      break;
  }
  const blob = new Blob([content], { type: mime });
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = `content.${extension}`;
  document.body.appendChild(a);
  a.click();
  a.remove();
  URL.revokeObjectURL(url);
}

export function shareOnLinkedIn(content) {
  return fetch('/api/share/linkedin', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ content })
  }).then(res => {
    if (!res.ok) {
      throw new Error('LinkedIn share failed');
    }
    return res.json();
  });
}

export function shareOnX(content) {
  return fetch('/api/share/x', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ content })
  }).then(res => {
    if (!res.ok) {
      throw new Error('X share failed');
    }
    return res.json();
  });
}
