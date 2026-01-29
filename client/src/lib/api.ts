/**
 * API client for ACL Anthology RAG backend.
 */

const API_BASE_URL = import.meta.env.VITE_API_URL || "";

export interface PaperMetadata {
  paper_id: string;
  title: string;
  abstract?: string;
  year?: string;
  authors?: string[];
  pdf_url?: string;
}

export interface SearchResult {
  paper: PaperMetadata;
  score: number;
}

/** Filter for year-based queries */
export interface YearFilter {
  exact?: number | null;
  min_year?: number | null;
  max_year?: number | null;
}

/** Structured filters for search queries */
export interface SearchFilters {
  year?: YearFilter | null;
  bibkey?: string | null;
  title_keywords?: string[] | null;
  language?: string | null;
  authors?: string[] | null;
  has_awards?: boolean | null;
  awards?: string[] | null;
}

/** Request options for search */
export interface SearchRequest {
  query?: string;
  top_k?: number;
}

/** Metadata sent at start of streaming response */
export interface StreamMetadata {
  original_query: string;
  results: SearchResult[];
  paper_id?: string | null;
  source_paper?: PaperMetadata | null;
  parsed_filters?: SearchFilters | null;
  // Monitoring data
  is_relevant?: boolean;
  semantic_query?: string | null;
  reformulated_queries?: string[] | null;
  timestamps?: { [key: string]: number } | null;
}

/** Callbacks for streaming search */
export interface StreamCallbacks {
  onMetadata?: (metadata: StreamMetadata) => void;
  onChunk?: (chunk: string) => void;
  onDone?: () => void;
  onError?: (error: Error) => void;
}

/**
 * Execute a streaming search query using Server-Sent Events.
 *
 * @param query - Search query string
 * @param callbacks - Callbacks for stream events
 * @param options - Optional search configuration
 * @returns AbortController to cancel the stream
 */
export function searchStream(
  query: string,
  callbacks: StreamCallbacks,
  options: {
    topK?: number;
  } = {}
): AbortController {
  const { topK = 5 } = options;
  const abortController = new AbortController();

  const requestBody: SearchRequest = {
    query,
    top_k: topK,
  };

  // Start the fetch request
  fetch(`${API_BASE_URL}/api/search`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Accept: "text/event-stream",
    },
    body: JSON.stringify(requestBody),
    signal: abortController.signal,
  })
    .then(async (response) => {
      if (!response.ok) {
        throw new Error(`Search failed: ${response.statusText}`);
      }

      const reader = response.body?.getReader();
      if (!reader) {
        throw new Error("No response body");
      }

      const decoder = new TextDecoder();
      let buffer = "";

      while (true) {
        const { done, value } = await reader.read();

        if (done) {
          break;
        }

        buffer += decoder.decode(value, { stream: true });

        // Process complete SSE messages
        const lines = buffer.split("\n");
        buffer = lines.pop() || ""; // Keep incomplete line in buffer

        let currentEvent = "";
        let currentData = "";

        for (const line of lines) {
          if (line.startsWith("event: ")) {
            currentEvent = line.slice(7);
          } else if (line.startsWith("data: ")) {
            currentData = line.slice(6);
          } else if (line === "" && currentEvent) {
            // Empty line signals end of message
            try {
              if (currentEvent === "metadata" && callbacks.onMetadata) {
                const metadata = JSON.parse(currentData) as StreamMetadata;
                callbacks.onMetadata(metadata);
              } else if (currentEvent === "chunk" && callbacks.onChunk) {
                const chunk = JSON.parse(currentData) as string;
                callbacks.onChunk(chunk);
              } else if (currentEvent === "done" && callbacks.onDone) {
                callbacks.onDone();
              } else if (currentEvent === "error" && callbacks.onError) {
                const errorData = JSON.parse(currentData);
                callbacks.onError(new Error(errorData.error || "Stream error"));
              }
            } catch (e) {
              console.error("Failed to parse SSE data:", e, currentData);
            }
            currentEvent = "";
            currentData = "";
          }
        }
      }

      // Call onDone if not already called
      if (callbacks.onDone) {
        callbacks.onDone();
      }
    })
    .catch((error) => {
      if (error.name === "AbortError") {
        // Stream was cancelled, not an error
        return;
      }
      if (callbacks.onError) {
        callbacks.onError(error);
      }
    });

  return abortController;
}
