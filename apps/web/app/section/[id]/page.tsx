import { notFound } from "next/navigation";
import Link from "next/link";
import { db } from "@/lib/db";
import {
  dcSections,
  dcSectionDeadlines,
  dcSectionAmounts,
  dcSectionRefs,
  dcSectionSimilarities,
  dcSectionSimilarityClassifications,
  dcSectionHighlights,
  dcSectionTags,
  dcGlobalTags,
} from "@/db/schema";
import { eq, or, and, sql } from "drizzle-orm";
import SimilarSectionsList from "@/components/SimilarSectionsList";
import { highlightPhrases } from "@/lib/highlight";
import Navigation from "@/components/Navigation";

interface Deadline {
  phrase: string;
  days: number;
  kind: string;
}

interface Amount {
  phrase: string;
  amountCents: number;
}

interface Reference {
  id: string;
  citation: string;
  heading: string;
  rawCite: string;
}

interface SimilarSection {
  id: string;
  citation: string;
  heading: string;
  similarity: number;
  classification?: string | null;
  explanation?: string | null;
  modelUsed?: string | null;
}

export default async function SectionPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = await params;

  // Fetch section data
  const [section] = await db
    .select()
    .from(dcSections)
    .where(eq(dcSections.id, id))
    .limit(1);

  if (!section) {
    notFound();
  }

  // Fetch deadlines
  const deadlines = await db
    .select({
      phrase: dcSectionDeadlines.phrase,
      days: dcSectionDeadlines.days,
      kind: dcSectionDeadlines.kind,
    })
    .from(dcSectionDeadlines)
    .where(eq(dcSectionDeadlines.sectionId, id));

  // Fetch dollar amounts
  const amounts = await db
    .select({
      phrase: dcSectionAmounts.phrase,
      amountCents: dcSectionAmounts.amountCents,
    })
    .from(dcSectionAmounts)
    .where(eq(dcSectionAmounts.sectionId, id));

  // Fetch cross-references (both directions)
  const referencesFrom = await db
    .select({
      id: dcSections.id,
      citation: dcSections.citation,
      heading: dcSections.heading,
      rawCite: dcSectionRefs.rawCite,
    })
    .from(dcSectionRefs)
    .innerJoin(dcSections, eq(dcSectionRefs.toId, dcSections.id))
    .where(eq(dcSectionRefs.fromId, id));

  const referencesTo = await db
    .select({
      id: dcSections.id,
      citation: dcSections.citation,
      heading: dcSections.heading,
      rawCite: dcSectionRefs.rawCite,
    })
    .from(dcSectionRefs)
    .innerJoin(dcSections, eq(dcSectionRefs.fromId, dcSections.id))
    .where(eq(dcSectionRefs.toId, id));

  // Fetch similar sections (both directions: section_a and section_b) with classifications
  const similarFromA = await db
    .select({
      id: dcSections.id,
      citation: dcSections.citation,
      heading: dcSections.heading,
      similarity: dcSectionSimilarities.similarity,
      classification: dcSectionSimilarityClassifications.classification,
      explanation: dcSectionSimilarityClassifications.explanation,
      modelUsed: dcSectionSimilarityClassifications.modelUsed,
    })
    .from(dcSectionSimilarities)
    .innerJoin(dcSections, eq(dcSectionSimilarities.sectionB, dcSections.id))
    .leftJoin(
      dcSectionSimilarityClassifications,
      and(
        eq(dcSectionSimilarityClassifications.sectionA, dcSectionSimilarities.sectionA),
        eq(dcSectionSimilarityClassifications.sectionB, dcSectionSimilarities.sectionB)
      )
    )
    .where(eq(dcSectionSimilarities.sectionA, id))
    .orderBy(sql`${dcSectionSimilarities.similarity} DESC`)
    .limit(5);

  const similarFromB = await db
    .select({
      id: dcSections.id,
      citation: dcSections.citation,
      heading: dcSections.heading,
      similarity: dcSectionSimilarities.similarity,
      classification: dcSectionSimilarityClassifications.classification,
      explanation: dcSectionSimilarityClassifications.explanation,
      modelUsed: dcSectionSimilarityClassifications.modelUsed,
    })
    .from(dcSectionSimilarities)
    .innerJoin(dcSections, eq(dcSectionSimilarities.sectionA, dcSections.id))
    .leftJoin(
      dcSectionSimilarityClassifications,
      and(
        eq(dcSectionSimilarityClassifications.sectionA, dcSectionSimilarities.sectionA),
        eq(dcSectionSimilarityClassifications.sectionB, dcSectionSimilarities.sectionB)
      )
    )
    .where(eq(dcSectionSimilarities.sectionB, id))
    .orderBy(sql`${dcSectionSimilarities.similarity} DESC`)
    .limit(5);

  // Combine and sort similar sections
  const similarSections = [...similarFromA, ...similarFromB]
    .sort((a, b) => b.similarity - a.similarity)
    .slice(0, 5);

  // Fetch reporting highlight phrases
  const phrasesToHighlight = await db
    .select({
      phrase: dcSectionHighlights.phrase,
    })
    .from(dcSectionHighlights)
    .where(eq(dcSectionHighlights.sectionId, id));

  // Fetch reporting tags
  const sectionTags = await db
    .select({
      tag: dcGlobalTags.tag,
    })
    .from(dcSectionTags)
    .innerJoin(dcGlobalTags, eq(dcSectionTags.tag, dcGlobalTags.tag))
    .where(eq(dcSectionTags.sectionId, id));

  // Apply highlighting to section HTML if there are phrases
  const highlightedHtml = section.hasReporting && phrasesToHighlight.length > 0
    ? highlightPhrases(section.textHtml, phrasesToHighlight.map(h => h.phrase))
    : section.textHtml;

  // Format currency
  const formatCurrency = (cents: number) => {
    return new Intl.NumberFormat("en-US", {
      style: "currency",
      currency: "USD",
      minimumFractionDigits: 2,
    }).format(cents / 100);
  };

  const hasObligations =
    deadlines.length > 0 || amounts.length > 0 || referencesFrom.length > 0;

  return (
    <>
      <Navigation breadcrumbs={[
        { label: "Home", href: "/" },
        { label: "Search", href: "/search" },
        { label: section.citation }
      ]} />
      <div className="min-h-screen bg-slate-50 py-8 px-4">
        <div className="max-w-4xl mx-auto">
          {/* Header */}
          <div className="bg-white rounded-lg border border-slate-200 shadow-sm p-6 mb-6">
            {/* Breadcrumbs */}
            <div className="text-sm text-slate-500 mb-3 flex items-center gap-2">
              <span>{section.titleLabel}</span>
              <span className="text-slate-400">›</span>
              <span>{section.chapterLabel}</span>
              <span className="text-slate-400">›</span>
              <span className="font-mono text-teal-700 font-medium">{section.citation}</span>
            </div>

            {/* Heading */}
            <h1 className="text-3xl font-bold text-slate-900 mb-4">
              {section.heading}
            </h1>

            {/* Citation */}
            <div className="text-slate-600">
              <span className="font-semibold">Citation:</span>{" "}
              <span className="font-mono">{section.citation}</span>
            </div>
          </div>

          {/* Reporting Requirements */}
          {section.hasReporting && (
            <div className="bg-violet-50 border border-violet-200 rounded-lg p-6 mb-6 shadow-sm">
              <div className="flex items-center gap-2 mb-3 flex-wrap">
                <span className="inline-block px-3 py-1 bg-violet-600 text-white text-sm font-semibold rounded-full">
                  Reporting Requirement
                </span>
                {sectionTags.length > 0 && (
                  <div className="flex gap-2 flex-wrap">
                    {sectionTags.map((tagObj, index) => (
                      <span
                        key={index}
                        className="inline-block px-2 py-0.5 bg-violet-100 text-violet-800 text-xs font-medium rounded"
                      >
                        {tagObj.tag}
                      </span>
                    ))}
                  </div>
                )}
              </div>
              {section.reportingSummary && (
                <p className="text-slate-700 text-sm leading-relaxed">
                  {section.reportingSummary}
                </p>
              )}
            </div>
          )}

          {/* Main Content */}
          <div className="bg-white rounded-lg border border-slate-200 shadow-sm p-6 mb-6">
            <h2 className="text-xl font-semibold text-slate-900 mb-4">
              Section Text
            </h2>
            <div
              className="prose prose-sm max-w-none text-slate-700 leading-relaxed"
              dangerouslySetInnerHTML={{ __html: highlightedHtml }}
            />
          </div>

          {/* Similar Sections */}
          <SimilarSectionsList
            currentSectionId={id}
            currentSectionCitation={section.citation}
            similarSections={similarSections}
          />

          {/* Obligations */}
          {hasObligations && (
            <div className="bg-white rounded-lg border border-slate-200 shadow-sm p-6 mb-6">
              <h2 className="text-xl font-semibold text-slate-900 mb-4">
                Obligations & References
              </h2>

              {/* Deadlines */}
              {deadlines.length > 0 && (
                <div className="mb-6">
                  <h3 className="text-lg font-medium text-slate-800 mb-3">
                    Deadlines & Time Requirements ({deadlines.length})
                  </h3>
                  <div className="space-y-3">
                    {deadlines.map((deadline, index) => (
                      <div
                        key={index}
                        className="flex gap-3 p-4 bg-amber-50 border border-amber-200 rounded-lg"
                      >
                        <div className="flex-shrink-0">
                          <span className="inline-block px-3 py-1 bg-amber-600 text-white text-sm font-semibold rounded-full">
                            {deadline.days} day{deadline.days !== 1 ? "s" : ""}
                          </span>
                        </div>
                        <div className="flex-1">
                          <p className="text-amber-900 text-sm leading-relaxed">
                            ...{deadline.phrase}...
                          </p>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* Dollar Amounts */}
              {amounts.length > 0 && (
                <div className="mb-6">
                  <h3 className="text-lg font-medium text-slate-800 mb-3">
                    Dollar Amounts ({amounts.length})
                  </h3>
                  <div className="space-y-3">
                    {amounts.map((amount, index) => (
                      <div
                        key={index}
                        className="flex gap-3 p-4 bg-emerald-50 border border-emerald-200 rounded-lg"
                      >
                        <div className="flex-shrink-0">
                          <span className="inline-block px-3 py-1 bg-emerald-600 text-white text-sm font-semibold rounded-full font-mono">
                            {formatCurrency(amount.amountCents)}
                          </span>
                        </div>
                        <div className="flex-1">
                          <p className="text-emerald-900 text-sm leading-relaxed">
                            ...{amount.phrase}...
                          </p>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* Cross-References From */}
              {referencesFrom.length > 0 && (
                <div className="mb-6">
                  <h3 className="text-lg font-medium text-slate-800 mb-3">
                    References From This Section ({referencesFrom.length})
                  </h3>
                  <div className="space-y-2">
                    {referencesFrom.map((ref, index) => (
                      <Link
                        key={index}
                        href={`/section/${ref.id}`}
                        className="block p-3 bg-blue-50 border border-blue-200 rounded-lg hover:border-blue-300 hover:shadow-sm transition-all"
                      >
                        <div className="flex items-center gap-2">
                          <span className="font-mono text-sm text-blue-600 font-medium">
                            {ref.citation}
                          </span>
                          <span className="text-slate-600">→</span>
                          <span className="text-slate-700 text-sm">
                            {ref.heading}
                          </span>
                        </div>
                      </Link>
                    ))}
                  </div>
                </div>
              )}

              {/* Cross-References To */}
              {referencesTo.length > 0 && (
                <div>
                  <h3 className="text-lg font-medium text-slate-800 mb-3">
                    References To This Section ({referencesTo.length})
                  </h3>
                  <div className="space-y-2">
                    {referencesTo.map((ref, index) => (
                      <Link
                        key={index}
                        href={`/section/${ref.id}`}
                        className="block p-3 bg-indigo-50 border border-indigo-200 rounded-lg hover:border-indigo-300 hover:shadow-sm transition-all"
                      >
                        <div className="flex items-center gap-2">
                          <span className="font-mono text-sm text-indigo-600 font-medium">
                            {ref.citation}
                          </span>
                          <span className="text-slate-600">←</span>
                          <span className="text-slate-700 text-sm">
                            {ref.heading}
                          </span>
                        </div>
                      </Link>
                    ))}
                  </div>
                </div>
              )}
            </div>
          )}

          {/* Empty State */}
          {!hasObligations && similarSections.length === 0 && (
            <div className="bg-white rounded-lg border border-slate-200 shadow-sm p-8 text-center">
              <p className="text-slate-500">
                No deadlines, dollar amounts, cross-references, or similar sections found.
              </p>
            </div>
          )}
        </div>
      </div>
    </>
  );
}
