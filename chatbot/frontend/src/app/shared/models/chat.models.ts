// ── WebSocket outgoing ────────────────────────────────────────────────────────

export interface MsgIn {
  role: 'user' | 'assistant';
  content: string;
}

export interface WsOutgoing {
  type: 'message' | 'ping';
  conversation_id?: string;
  messages?: MsgIn[];
  model?: string;
  temperature?: number;
}

// ── WebSocket incoming frames ─────────────────────────────────────────────────

export interface WsDelta {
  type: 'delta';
  content: string;
}

export interface WsDone {
  type: 'done';
  conversation_id: string;
  token_count: number;
  provider: string;
  model: string;
}

export interface WsError {
  type: 'error';
  message: string;
  code: number;
}

export interface WsPong {
  type: 'pong';
}

export interface WsTitle {
  type: 'title';
  conversation_id: string;
  title: string;
}

export interface WsClarificationRequest {
  type: 'clarification_request';
  message: string;
  candidates: string[];
}

export interface WsProviderInfo {
  provider: string;
  models: string[];
  default_model: string;
}

export interface WsProviders {
  type: 'providers';
  data: WsProviderInfo[];
}

export type WsIncoming =
  | WsDelta
  | WsDone
  | WsError
  | WsPong
  | WsTitle
  | WsProviders
  | WsClarificationRequest;

// ── Application models ────────────────────────────────────────────────────────

export interface ClarificationState {
  message: string;
  candidates: string[];
  answered: boolean;
}

export interface ChatMessage {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  provider?: string;
  model?: string;
  tokenCount?: number;
  streaming?: boolean;
  error?: boolean;
  clarification?: ClarificationState;
}

export interface Conversation {
  id: string;
  title: string;
  messages: ChatMessage[];
  createdAt: Date;
  updatedAt: Date;
}
