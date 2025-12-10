import React from 'react';
import { useConversation } from '../state/ConversationContext';

export default function HistoryPanel() {
  const { history, clearHistory } = useConversation();

  return (
    <div className="history-panel">
      <div className="history-header">
        <h2>History</h2>
        <button onClick={clearHistory}>Clear history</button>
      </div>
      <ul>
        {history.map((entry, idx) => (
          <li key={idx}>{entry}</li>
        ))}
      </ul>
    </div>
  );
}
