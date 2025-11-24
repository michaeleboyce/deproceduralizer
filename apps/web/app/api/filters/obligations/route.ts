import { createFilterHandler, filterQueries } from '@/lib/api/filters';

/**
 * GET /api/filters/obligations
 *
 * Returns list of unique obligation categories that have results
 * matching the provided filters
 *
 * Query params:
 * - jurisdiction: string (default: "dc")
 * - title: string (optional) - filter by title
 * - chapter: string (optional) - filter by chapter
 * - hasReporting: boolean (optional) - filter by reporting requirement
 * - query: string (optional) - full-text search query
 */
export const GET = createFilterHandler({
    type: 'complex',
    resultField: 'categories',
    buildQuery: filterQueries.obligations,
    transformResult: (rows) => rows.map((row: any) => row.category),
});
