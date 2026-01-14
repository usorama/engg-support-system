/**
 * API Client - Handles all communication with ESS Gateway
 *
 * Provides typed methods for all Gateway endpoints with proper error handling,
 * retry logic, and authentication.
 */

import type {
  QueryRequest,
  ConversationContinueRequest,
  FeedbackRequest,
  GatewayResponse,
  HealthResponse,
  ProjectsResponse,
  APIError,
} from "../types/api";

// API Configuration
const API_BASE_URL = import.meta.env.VITE_API_URL || "/api";
const API_KEY = import.meta.env.VITE_ESS_API_KEY || "";
const REQUEST_TIMEOUT = 60000; // 60 seconds for synthesis

/**
 * Custom error class for API errors
 */
export class APIClientError extends Error {
  constructor(
    message: string,
    public statusCode: number,
    public retryAfter?: number
  ) {
    super(message);
    this.name = "APIClientError";
  }
}

/**
 * Create headers with authentication
 */
function createHeaders(): HeadersInit {
  const headers: HeadersInit = {
    "Content-Type": "application/json",
  };

  if (API_KEY) {
    headers["Authorization"] = `Bearer ${API_KEY}`;
  }

  return headers;
}

/**
 * Generic fetch wrapper with timeout and error handling
 */
async function fetchWithTimeout<T>(
  url: string,
  options: RequestInit,
  timeout: number = REQUEST_TIMEOUT
): Promise<T> {
  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), timeout);

  try {
    const response = await fetch(url, {
      ...options,
      signal: controller.signal,
    });

    clearTimeout(timeoutId);

    // Handle rate limiting
    if (response.status === 429) {
      const data = (await response.json()) as APIError;
      throw new APIClientError(
        data.message || "Rate limited",
        429,
        data.retryAfter
      );
    }

    // Handle authentication errors
    if (response.status === 401) {
      throw new APIClientError("Unauthorized - check API key", 401);
    }

    if (response.status === 403) {
      throw new APIClientError("Forbidden - invalid API key", 403);
    }

    // Handle server errors
    if (!response.ok) {
      const data = (await response.json().catch(() => ({
        error: "Unknown error",
        message: `HTTP ${response.status}`,
      }))) as APIError;
      throw new APIClientError(data.message || data.error, response.status);
    }

    return response.json() as Promise<T>;
  } catch (error) {
    clearTimeout(timeoutId);

    if (error instanceof APIClientError) {
      throw error;
    }

    if (error instanceof Error && error.name === "AbortError") {
      throw new APIClientError("Request timeout", 408);
    }

    throw new APIClientError(
      error instanceof Error ? error.message : "Network error",
      0
    );
  }
}

/**
 * API Client methods
 */
export const apiClient = {
  /**
   * Health check endpoint
   */
  async getHealth(): Promise<HealthResponse> {
    return fetchWithTimeout<HealthResponse>(
      `${API_BASE_URL}/health`,
      {
        method: "GET",
      },
      10000 // 10 second timeout for health checks
    );
  },

  /**
   * Get list of available projects
   */
  async getProjects(): Promise<ProjectsResponse> {
    return fetchWithTimeout<ProjectsResponse>(
      `${API_BASE_URL}/projects`,
      {
        method: "GET",
        headers: createHeaders(),
      },
      10000
    );
  },

  /**
   * One-shot query
   */
  async query(request: QueryRequest): Promise<GatewayResponse> {
    return fetchWithTimeout<GatewayResponse>(`${API_BASE_URL}/query`, {
      method: "POST",
      headers: createHeaders(),
      body: JSON.stringify(request),
    });
  },

  /**
   * Start a new conversation
   */
  async startConversation(request: QueryRequest): Promise<GatewayResponse> {
    return fetchWithTimeout<GatewayResponse>(`${API_BASE_URL}/conversation`, {
      method: "POST",
      headers: createHeaders(),
      body: JSON.stringify({
        ...request,
        mode: "conversational",
      }),
    });
  },

  /**
   * Continue an existing conversation with answers
   */
  async continueConversation(
    conversationId: string,
    request: ConversationContinueRequest
  ): Promise<GatewayResponse> {
    return fetchWithTimeout<GatewayResponse>(
      `${API_BASE_URL}/conversation/${conversationId}/continue`,
      {
        method: "POST",
        headers: createHeaders(),
        body: JSON.stringify(request),
      }
    );
  },

  /**
   * Abort a conversation
   */
  async abortConversation(conversationId: string): Promise<void> {
    await fetchWithTimeout<{ status: string }>(
      `${API_BASE_URL}/conversation/${conversationId}`,
      {
        method: "DELETE",
        headers: createHeaders(),
      }
    );
  },

  /**
   * Submit feedback for a query
   */
  async submitFeedback(request: FeedbackRequest): Promise<void> {
    await fetchWithTimeout<{ status: string }>(`${API_BASE_URL}/feedback`, {
      method: "POST",
      headers: createHeaders(),
      body: JSON.stringify(request),
    });
  },
};

export default apiClient;
