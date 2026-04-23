/**
 * API route — proxies copilot queries to ai-core service.
 * Injects the user's auth token and organisation context from the session.
 */
import { NextRequest, NextResponse } from 'next/server';
import { createServerClient } from '@supabase/ssr';
import { cookies } from 'next/headers';
import { queryCopilot } from '@/lib/api/ai-core';
import type { CopilotQueryRequest, InteractionType } from '@ai-ops/shared-types';

export async function POST(request: NextRequest) {
  const cookieStore = cookies();

  const supabase = createServerClient(
    process.env.NEXT_PUBLIC_SUPABASE_URL!,
    process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!,
    {
      cookies: {
        get: (name) => cookieStore.get(name)?.value,
      },
    }
  );

  const { data: { session } } = await supabase.auth.getSession();

  if (!session) {
    return NextResponse.json({ error: { message: 'Unauthorised' } }, { status: 401 });
  }

  const body = await request.json().catch(() => null);
  if (!body?.query || !body?.context) {
    return NextResponse.json({ error: { message: 'Missing required fields' } }, { status: 400 });
  }

  const organisationId = session.user.app_metadata?.['organisation_id'];
  if (!organisationId) {
    return NextResponse.json({ error: { message: 'Missing organisation context' } }, { status: 403 });
  }

  const aiRequest: CopilotQueryRequest = {
    query: body.query,
    context: {
      guest_id: body.context.guest_id,
      stay_id: body.context.stay_id,
      interaction_type: (body.context.interaction_type ?? 'general') as InteractionType,
    },
    organisation_id: organisationId as string,
    user_id: session.user.id,
  };

  try {
    const result = await queryCopilot(aiRequest, session.access_token);
    return NextResponse.json(result);
  } catch (err) {
    console.error('[copilot/query]', err);
    return NextResponse.json(
      { error: { message: 'AI service temporarily unavailable' } },
      { status: 503 }
    );
  }
}
