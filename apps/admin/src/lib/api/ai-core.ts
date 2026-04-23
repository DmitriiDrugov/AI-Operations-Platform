/**
 * Typed client for the Python AI Core service.
 * Consumed by the admin app's server components and route handlers.
 * All requests proxy through Next.js API routes to avoid exposing the AI Core URL to the browser.
 */
import type {
  ClassifyLeadRequest,
  ClassifyLeadResponse,
  CopilotQueryRequest,
  CopilotQueryResponse,
  KnowledgeSearchRequest,
  KnowledgeSearchResponse,
} from '@ai-ops/shared-types';

const AI_CORE_URL = process.env.AI_CORE_SERVICE_URL ?? 'http://localhost:8000';

async function post<TReq, TRes>(
  path: string,
  body: TReq,
  authToken: string
): Promise<TRes> {
  const response = await fetch(`${AI_CORE_URL}${path}`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      Authorization: `Bearer ${authToken}`,
    },
    body: JSON.stringify(body),
  });

  if (!response.ok) {
    const error = await response.json().catch(() => ({ error: { message: 'Unknown error' } }));
    throw new Error(error?.error?.message ?? `AI Core error: ${response.status}`);
  }

  return response.json() as Promise<TRes>;
}

export async function queryCopilot(
  request: CopilotQueryRequest,
  authToken: string
): Promise<CopilotQueryResponse> {
  return post<CopilotQueryRequest, CopilotQueryResponse>(
    '/v1/copilot/query',
    request,
    authToken
  );
}

export async function classifyLead(
  request: ClassifyLeadRequest,
  authToken: string
): Promise<ClassifyLeadResponse> {
  return post<ClassifyLeadRequest, ClassifyLeadResponse>(
    '/v1/leads/classify',
    request,
    authToken
  );
}

export async function searchKnowledge(
  request: KnowledgeSearchRequest,
  authToken: string
): Promise<KnowledgeSearchResponse> {
  return post<KnowledgeSearchRequest, KnowledgeSearchResponse>(
    '/v1/knowledge/search',
    request,
    authToken
  );
}
