import { NextResponse } from 'next/server';

const SNAPSHOT_URL =
  'https://raw.githubusercontent.com/executiveusa/YAPPYVERSE-FACTORY/main/docs/pauliverse/seeds/core-portfolio.snapshot.json';

export const dynamic = 'force-dynamic';

export async function GET() {
  try {
    const response = await fetch(SNAPSHOT_URL, {
      cache: 'no-store',
      headers: { Accept: 'application/json' },
    });

    if (!response.ok) {
      return NextResponse.json(
        { error: 'authoritative_snapshot_unavailable', upstream_status: response.status },
        { status: 503, headers: { 'Cache-Control': 'no-store' } },
      );
    }

    const snapshot = await response.json();
    const valid =
      snapshot?.schema_version === 1 &&
      typeof snapshot?.generated_at === 'string' &&
      Array.isArray(snapshot?.nodes) &&
      Array.isArray(snapshot?.edges) &&
      snapshot.nodes.every((node: unknown) => {
        if (!node || typeof node !== 'object') return false;
        const candidate = node as Record<string, unknown>;
        return typeof candidate.id === 'string' && typeof candidate.name === 'string' && typeof candidate.type === 'string';
      });

    if (!valid) {
      return NextResponse.json(
        { error: 'authoritative_snapshot_schema_invalid' },
        { status: 502, headers: { 'Cache-Control': 'no-store' } },
      );
    }

    return NextResponse.json(snapshot, {
      status: 200,
      headers: {
        'Cache-Control': 'no-store, max-age=0',
        'X-Pauliverse-Source': 'YAPPYVERSE-FACTORY',
        'X-Pauliverse-Schema': '1',
      },
    });
  } catch (error) {
    return NextResponse.json(
      {
        error: 'authoritative_snapshot_fetch_failed',
        detail: error instanceof Error ? error.message : 'unknown error',
      },
      { status: 503, headers: { 'Cache-Control': 'no-store' } },
    );
  }
}
