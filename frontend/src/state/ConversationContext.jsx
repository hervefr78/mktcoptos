import React, { createContext, useContext, useEffect, useState } from 'react';
import { loadHistory, saveHistory, clearHistoryStorage } from '../utils/history';

const ConversationContext = createContext();

export function ConversationProvider({ children }) {
  const [history, setHistory] = useState(() => loadHistory());

  useEffect(() => {
    saveHistory(history);
  }, [history]);

  const addMessage = (message) => {
    setHistory((h) => [...h, message]);
  };

  const clearHistory = () => {
    setHistory([]);
    clearHistoryStorage();
  };

  return (
    <ConversationContext.Provider value={{ history, addMessage, clearHistory }}>
      {children}
    </ConversationContext.Provider>
  );
}

export function useConversation() {
  const ctx = useContext(ConversationContext);
  if (!ctx) {
    throw new Error('useConversation must be used within a ConversationProvider');
  }
  return ctx;
}
