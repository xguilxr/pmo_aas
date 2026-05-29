import { apiFetch } from "@/lib/api";

/** US-165 — cliente del asistente IA conversacional (widget global). */

export type AssistantAction = {
  type: "navigate" | "none";
  path?: string | null;
  label?: string | null;
};

export type AssistantChatResponse = {
  conversation_id: string;
  message: string;
  actions: AssistantAction[];
};

export type AssistantMessage = {
  id: string;
  role: "user" | "assistant";
  content: string;
  actions: AssistantAction[];
  created_at: string;
};

export type AssistantConversation = {
  id: string;
  title: string | null;
  created_at: string;
  updated_at: string;
};

export type AssistantConversationDetail = AssistantConversation & {
  messages: AssistantMessage[];
};

export function sendAssistantMessage(input: {
  message: string;
  conversation_id?: string | null;
  page_context?: string | null;
}): Promise<AssistantChatResponse> {
  return apiFetch<AssistantChatResponse>("/api/v1/assistant/chat", {
    method: "POST",
    body: {
      message: input.message,
      conversation_id: input.conversation_id ?? null,
      page_context: input.page_context ?? null,
    },
  });
}

export function listAssistantConversations(): Promise<AssistantConversation[]> {
  return apiFetch<AssistantConversation[]>("/api/v1/assistant/conversations");
}

export function getAssistantConversation(
  id: string,
): Promise<AssistantConversationDetail> {
  return apiFetch<AssistantConversationDetail>(
    `/api/v1/assistant/conversations/${id}`,
  );
}

export function deleteAssistantConversation(id: string): Promise<void> {
  return apiFetch<void>(`/api/v1/assistant/conversations/${id}`, {
    method: "DELETE",
  });
}
