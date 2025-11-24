import { NextResponse } from 'next/server';
import { validateJurisdiction, config } from '@/lib/config';

/**
 * Create a standardized JSON error response.
 */
export function apiError(message: string, status: number = 500) {
    return NextResponse.json({ error: message }, { status });
}

/**
 * Extract common query parameters from a request.
 * Handles jurisdiction validation and pagination defaults.
 */
export function extractCommonParams(searchParams: URLSearchParams) {
    const jurisdiction = validateJurisdiction(searchParams.get('jurisdiction'));
    const limitParam = parseInt(searchParams.get('limit') || '0', 10);
    const limit = limitParam > 0
        ? Math.min(limitParam, config.pagination.maxLimit)
        : config.pagination.defaultLimit;
    const offset = parseInt(searchParams.get('offset') || '0', 10);
    const page = parseInt(searchParams.get('page') || '1', 10);

    return { jurisdiction, limit, offset, page };
}

/**
 * Extract filter parameters commonly used across routes.
 */
export function extractFilterParams(searchParams: URLSearchParams) {
    return {
        title: searchParams.get('title')?.trim() || null,
        chapter: searchParams.get('chapter')?.trim() || null,
        hasReporting: searchParams.get('hasReporting') === 'true',
        query: searchParams.get('query')?.trim() || searchParams.get('searchQuery')?.trim() || null,
    };
}

/**
 * Common filter parameters type
 */
export type FilterParams = ReturnType<typeof extractFilterParams>;
export type CommonParams = ReturnType<typeof extractCommonParams>;
