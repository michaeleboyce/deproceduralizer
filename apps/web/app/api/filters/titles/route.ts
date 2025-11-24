import { createFilterHandler } from '@/lib/api/filters';
import { sections } from '@/db/schema';

/**
 * GET /api/filters/titles
 *
 * Returns list of distinct titles for filter dropdown
 */
export const GET = createFilterHandler({
    type: 'simple',
    resultField: 'titles',
    selectField: sections.titleLabel,
});
