export async function streamAgent(agent, params, onToken) {
  const response = await fetch(`/agents/${agent}/stream`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ params }),
  });

  if (!response.body) {
    throw new Error('Streaming not supported');
  }

  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = '';

  while (true) {
    const { value, done } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });
    const parts = buffer.split('\n\n');
    buffer = parts.pop();
    for (const part of parts) {
      if (part.startsWith('data:')) {
        const token = part.replace('data:', '').trim();
        onToken(token);
      }
    }
  }
}
