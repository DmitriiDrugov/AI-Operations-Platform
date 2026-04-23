/**
 * React hook for the AI Copilot panel.
 * Manages conversation history, loading state, and error handling.
 * Calls the Next.js API route which proxies to ai-core.
 */
import { useState, useCallback } from 'react';
import type { CopilotQueryResponse, InteractionType } from '@ai-ops/shared-types';

interface Message {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  citations?: CopilotQueryResponse['citations'];
  suggestedActions?: CopilotQueryResponse['suggested_actions'];
  timestamp: Date;
}

interface UseCopilotOptions {
  guestId?: string;
  stayId?: string;
  interactionType?: InteractionType;
}

export function useCopilot(options: UseCopilotOptions = {}) {
  const [messages, setMessages] = useState<Message[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const sendMessage = useCallback(
    async (query: string) => {
      if (!query.trim() || isLoading) return;

      const userMessage: Message = {
        id: crypto.randomUUID(),
        role: 'user',
        content: query,
        timestamp: new Date(),
      };

      setMessages((prev) => [...prev, userMessage]);
      setIsLoading(true);
      setError(null);

      try {
        const response = await fetch('/api/copilot/query', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            query,
            context: {
              guest_id: options.guestId,
              stay_id: options.stayId,
              interaction_type: options.interactionType ?? 'general',
            },
          }),
        });

        if (!response.ok) {
          throw new Error('AI service error. Please try again.');
        }

        const data: CopilotQueryResponse = await response.json();

        const assistantMessage: Message = {
          id: data.interaction_id,
          role: 'assistant',
          content: data.response_text,
          citations: data.citations,
          suggestedActions: data.suggested_actions,
          timestamp: new Date(),
        };

        setMessages((prev) => [...prev, assistantMessage]);
      } catch (err) {
        setError(err instanceof Error ? err.message : 'An unexpected error occurred');
      } finally {
        setIsLoading(false);
      }
    },
    [isLoading, options.guestId, options.stayId, options.interactionType]
  );

  const clearHistory = useCallback(() => {
    setMessages([]);
    setError(null);
  }, []);

  return {
    messages,
    isLoading,
    error,
    sendMessage,
    clearHistory,
  };
}
