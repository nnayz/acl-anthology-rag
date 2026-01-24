/**
 * API client for ACL Anthology RAG backend.
 */

const API_BASE_URL = import.meta.env.VITE_API_URL || "";

export type QueryType = "natural_language" | "paper_id";

export interface QueryClassification {
  query_type: QueryType;
  original_query: string;
  paper_id: string | null;
  is_valid: boolean;
}

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

export interface SearchResponse {
  query_type: QueryType;
  original_query: string;
  results: SearchResult[];
  paper_id: string | null;
  /** The source paper for paper ID queries (the paper the user referenced) */
  source_paper?: PaperMetadata;
  /** LLM-generated natural language response (markdown format) */
  response?: string;
}

/**
 * Classify a query to determine if it's a paper ID or natural language.
 */
export async function classifyQuery(
  query: string
): Promise<QueryClassification> {
  const response = await fetch(`${API_BASE_URL}/api/classify`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({ query }),
  });

  if (!response.ok) {
    throw new Error(`Classification failed: ${response.statusText}`);
  }

  return response.json();
}

/**
 * Execute a search query against the ACL Anthology corpus.
 */
export async function search(
  query: string,
  topK: number = 5
): Promise<SearchResponse> {
  const response = await fetch(`${API_BASE_URL}/api/search`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({ query, top_k: topK }),
  });

  if (!response.ok) {
    throw new Error(`Search failed: ${response.statusText}`);
  }

  return response.json();
}

/**
 * Fetch paper metadata by ACL paper ID.
 */
export async function getPaper(paperId: string): Promise<PaperMetadata | null> {
  const response = await fetch(
    `${API_BASE_URL}/api/paper/${encodeURIComponent(paperId)}`
  );

  if (response.status === 404) {
    return null;
  }

  if (!response.ok) {
    throw new Error(`Failed to fetch paper: ${response.statusText}`);
  }

  return response.json();
}
