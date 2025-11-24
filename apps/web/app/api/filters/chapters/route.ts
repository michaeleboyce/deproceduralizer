import { createFilterHandler } from '@/lib/api/filters';
import { sections } from '@/db/schema';

/**
 * GET /api/filters/chapters?title=Title+1
 *
 * Returns list of distinct chapters, optionally filtered by title
 */
export const GET = createFilterHandler({
    type: 'simple',
    resultField: 'chapters',
    selectField: sections.chapterLabel,
});
