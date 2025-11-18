import { notFound } from "next/navigation";
import Link from "next/link";
import { db } from "@/lib/db";
import {
  sections,
  sectionDeadlines,
  sectionAmounts,
  obligations,
  sectionRefs,
  sectionSimilarities,
  sectionSimilarityClassifications,
  sectionHighlights,
  sectionTags,
  globalTags,
} from "@/db/schema";
import { eq, or, and, sql } from "drizzle-orm";
import SimilarSectionsList from "@/components/SimilarSectionsList";
import { highlightPhrases } from "@/lib/highlight";
import Navigation from "@/components/Navigation";
import MobileTableOfContents from "@/components/MobileTableOfContents";

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

  // Hardcode jurisdiction to 'dc' for now (transparent to user)
  const jurisdiction = 'dc';

  // Fetch section data
  const [section] = await db
    .select()
    .from(sections)
    .where(and(
      eq(sections.jurisdiction, jurisdiction),
      eq(sections.id, id)
    ))
    .limit(1);

  if (!section) {
    notFound();
  }

  // Fetch deadlines
  const deadlines = await db
    .select({
      phrase: sectionDeadlines.phrase,
      days: sectionDeadlines.days,
      kind: sectionDeadlines.kind,
    })
    .from(sectionDeadlines)
    .where(and(
      eq(sectionDeadlines.jurisdiction, jurisdiction),
      eq(sectionDeadlines.sectionId, id)
    ));

  // Fetch dollar amounts
  const amounts = await db
    .select({
      phrase: sectionAmounts.phrase,
      amountCents: sectionAmounts.amountCents,
    })
    .from(sectionAmounts)
    .where(and(
      eq(sectionAmounts.jurisdiction, jurisdiction),
      eq(sectionAmounts.sectionId, id)
    ));

  // Fetch enhanced obligations (categorized obligations from LLM analysis)
  const enhancedObligations = await db
    .select({
      category: obligations.category,
      phrase: obligations.phrase,
      value: obligations.value,
      unit: obligations.unit,
      confidence: obligations.confidence,
    })
    .from(obligations)
    .where(and(
      eq(obligations.jurisdiction, jurisdiction),
      eq(obligations.sectionId, id)
    ))
    .orderBy(obligations.category, sql`${obligations.value} DESC NULLS LAST`);

  // Group obligations by category for display
  const obligationsByCategory = enhancedObligations.reduce((acc, obl) => {
    if (!acc[obl.category]) {
      acc[obl.category] = [];
    }
    acc[obl.category].push(obl);
    return acc;
  }, {} as Record<string, typeof enhancedObligations>);

  // Fetch cross-references (both directions)
  const referencesFrom = await db
    .select({
      id: sections.id,
      citation: sections.citation,
      heading: sections.heading,
      rawCite: sectionRefs.rawCite,
    })
    .from(sectionRefs)
    .innerJoin(sections, and(
      eq(sectionRefs.jurisdiction, sections.jurisdiction),
      eq(sectionRefs.toId, sections.id)
    ))
    .where(and(
      eq(sectionRefs.jurisdiction, jurisdiction),
      eq(sectionRefs.fromId, id)
    ));

  const referencesTo = await db
    .select({
      id: sections.id,
      citation: sections.citation,
      heading: sections.heading,
      rawCite: sectionRefs.rawCite,
    })
    .from(sectionRefs)
    .innerJoin(sections, and(
      eq(sectionRefs.jurisdiction, sections.jurisdiction),
      eq(sectionRefs.fromId, sections.id)
    ))
    .where(and(
      eq(sectionRefs.jurisdiction, jurisdiction),
      eq(sectionRefs.toId, id)
    ));

  // Fetch similar sections (both directions: section_a and section_b) with classifications
  const similarFromA = await db
    .select({
      id: sections.id,
      citation: sections.citation,
      heading: sections.heading,
      similarity: sectionSimilarities.similarity,
      classification: sectionSimilarityClassifications.classification,
      explanation: sectionSimilarityClassifications.explanation,
      modelUsed: sectionSimilarityClassifications.modelUsed,
    })
    .from(sectionSimilarities)
    .innerJoin(sections, and(
      eq(sectionSimilarities.jurisdiction, sections.jurisdiction),
      eq(sectionSimilarities.sectionB, sections.id)
    ))
    .leftJoin(
      sectionSimilarityClassifications,
      and(
        eq(sectionSimilarityClassifications.jurisdiction, sectionSimilarities.jurisdiction),
        eq(sectionSimilarityClassifications.sectionA, sectionSimilarities.sectionA),
        eq(sectionSimilarityClassifications.sectionB, sectionSimilarities.sectionB)
      )
    )
    .where(and(
      eq(sectionSimilarities.jurisdiction, jurisdiction),
      eq(sectionSimilarities.sectionA, id)
    ))
    .orderBy(sql`${sectionSimilarities.similarity} DESC`)
    .limit(5);

  const similarFromB = await db
    .select({
      id: sections.id,
      citation: sections.citation,
      heading: sections.heading,
      similarity: sectionSimilarities.similarity,
      classification: sectionSimilarityClassifications.classification,
      explanation: sectionSimilarityClassifications.explanation,
      modelUsed: sectionSimilarityClassifications.modelUsed,
    })
    .from(sectionSimilarities)
    .innerJoin(sections, and(
      eq(sectionSimilarities.jurisdiction, sections.jurisdiction),
      eq(sectionSimilarities.sectionA, sections.id)
    ))
    .leftJoin(
      sectionSimilarityClassifications,
      and(
        eq(sectionSimilarityClassifications.jurisdiction, sectionSimilarities.jurisdiction),
        eq(sectionSimilarityClassifications.sectionA, sectionSimilarities.sectionA),
        eq(sectionSimilarityClassifications.sectionB, sectionSimilarities.sectionB)
      )
    )
    .where(and(
      eq(sectionSimilarities.jurisdiction, jurisdiction),
      eq(sectionSimilarities.sectionB, id)
    ))
    .orderBy(sql`${sectionSimilarities.similarity} DESC`)
    .limit(5);

  // Combine and sort similar sections
  const similarSections = [...similarFromA, ...similarFromB]
    .sort((a, b) => b.similarity - a.similarity)
    .slice(0, 5);

  // Fetch reporting highlight phrases
  const phrasesToHighlight = await db
    .select({
      phrase: sectionHighlights.phrase,
    })
    .from(sectionHighlights)
    .where(and(
      eq(sectionHighlights.jurisdiction, jurisdiction),
      eq(sectionHighlights.sectionId, id)
    ));

  // Fetch reporting tags
  const sectionTagsData = await db
    .select({
      tag: globalTags.tag,
    })
    .from(sectionTags)
    .innerJoin(globalTags, eq(sectionTags.tag, globalTags.tag))
    .where(and(
      eq(sectionTags.jurisdiction, jurisdiction),
      eq(sectionTags.sectionId, id)
    ));

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

  // Build table of contents
  const tocItems = [
    { id: "section-text", label: "Section Text" },
    similarSections.length > 0 && { id: "similar-sections", label: "Similar Sections" },
    enhancedObligations.length > 0 && { id: "extracted-obligations", label: "Extracted Obligations" },
    hasObligations && { id: "obligations-references", label: "Obligations & References" },
  ].filter(Boolean) as { id: string; label: string }[];

  return (
    <>
      <Navigation breadcrumbs={[
        { label: "Home", href: "/" },
        { label: "Search", href: "/search" },
        { label: section.citation }
      ]} />
      <div className="min-h-screen bg-slate-50 py-8 px-4">
        <div className="max-w-7xl mx-auto">
          {/* Mobile TOC - Sticky at top */}
          <MobileTableOfContents items={tocItems} />

          {/* Desktop Layout: Content + Sidebar */}
          <div className="lg:flex lg:gap-8">
            {/* Main Content */}
            <div className="flex-1 lg:max-w-4xl">
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
                {sectionTagsData.length > 0 && (
                  <div className="flex gap-2 flex-wrap">
                    {sectionTagsData.map((tagObj, index) => (
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
          <div id="section-text" className="bg-white rounded-lg border border-slate-200 shadow-sm p-6 mb-6 scroll-mt-20">
            <h2 className="text-xl font-semibold text-slate-900 mb-4">
              Section Text
            </h2>
            <div
              className="prose prose-sm max-w-none text-slate-700 leading-relaxed"
              dangerouslySetInnerHTML={{ __html: highlightedHtml }}
            />
          </div>

          {/* Similar Sections */}
          {similarSections.length > 0 && (
            <div id="similar-sections" className="scroll-mt-20">
              <SimilarSectionsList
                currentSectionId={id}
                currentSectionCitation={section.citation}
                similarSections={similarSections}
              />
            </div>
          )}

          {/* Enhanced Obligations */}
          {enhancedObligations.length > 0 && (
            <div id="extracted-obligations" className="bg-white rounded-lg border border-slate-200 shadow-sm p-6 mb-6 scroll-mt-20">
              <h2 className="text-xl font-semibold text-slate-900 mb-4">
                Extracted Obligations ({enhancedObligations.length})
              </h2>

              {/* Obligations grouped by category */}
              <div className="space-y-6">
                {/* Deadlines */}
                {obligationsByCategory.deadline && (
                  <div>
                    <h3 className="text-lg font-medium text-slate-800 mb-3">
                      ⏰ Deadlines & Time Requirements ({obligationsByCategory.deadline.length})
                    </h3>
                    <div className="space-y-2">
                      {obligationsByCategory.deadline.map((obl, index) => (
                        <div
                          key={index}
                          className="flex gap-3 p-3 bg-amber-50 border border-amber-200 rounded-lg"
                        >
                          {obl.value && obl.unit && (
                            <div className="flex-shrink-0">
                              <span className="inline-block px-3 py-1 bg-amber-600 text-white text-sm font-semibold rounded-full">
                                {obl.value} {obl.unit}
                              </span>
                            </div>
                          )}
                          <div className="flex-1">
                            <p className="text-amber-900 text-sm leading-relaxed">
                              {obl.phrase}
                            </p>
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>
                )}

                {/* Constraints */}
                {obligationsByCategory.constraint && (
                  <div>
                    <h3 className="text-lg font-medium text-slate-800 mb-3">
                      📋 Constraints & Requirements ({obligationsByCategory.constraint.length})
                    </h3>
                    <div className="space-y-2">
                      {obligationsByCategory.constraint.map((obl, index) => (
                        <div
                          key={index}
                          className="flex gap-3 p-3 bg-slate-50 border border-slate-200 rounded-lg"
                        >
                          {obl.value && obl.unit && (
                            <div className="flex-shrink-0">
                              <span className="inline-block px-3 py-1 bg-slate-600 text-white text-sm font-semibold rounded-full">
                                {obl.value} {obl.unit}
                              </span>
                            </div>
                          )}
                          <div className="flex-1">
                            <p className="text-slate-900 text-sm leading-relaxed">
                              {obl.phrase}
                            </p>
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>
                )}

                {/* Penalties */}
                {obligationsByCategory.penalty && (
                  <div>
                    <h3 className="text-lg font-medium text-slate-800 mb-3">
                      ⚠️ Penalties ({obligationsByCategory.penalty.length})
                    </h3>
                    <div className="space-y-2">
                      {obligationsByCategory.penalty.map((obl, index) => (
                        <div
                          key={index}
                          className="flex gap-3 p-3 bg-red-50 border border-red-200 rounded-lg"
                        >
                          {obl.value && obl.unit && (
                            <div className="flex-shrink-0">
                              <span className="inline-block px-3 py-1 bg-red-600 text-white text-sm font-semibold rounded-full">
                                {obl.value} {obl.unit}
                              </span>
                            </div>
                          )}
                          <div className="flex-1">
                            <p className="text-red-900 text-sm leading-relaxed">
                              {obl.phrase}
                            </p>
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>
                )}

                {/* Allocations */}
                {obligationsByCategory.allocation && (
                  <div>
                    <h3 className="text-lg font-medium text-slate-800 mb-3">
                      💰 Allocations & Amounts ({obligationsByCategory.allocation.length})
                    </h3>
                    <div className="space-y-2">
                      {obligationsByCategory.allocation.map((obl, index) => (
                        <div
                          key={index}
                          className="flex gap-3 p-3 bg-emerald-50 border border-emerald-200 rounded-lg"
                        >
                          {obl.value && obl.unit && (
                            <div className="flex-shrink-0">
                              <span className="inline-block px-3 py-1 bg-emerald-600 text-white text-sm font-semibold rounded-full">
                                {obl.value} {obl.unit}
                              </span>
                            </div>
                          )}
                          <div className="flex-1">
                            <p className="text-emerald-900 text-sm leading-relaxed">
                              {obl.phrase}
                            </p>
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            </div>
          )}

          {/* Obligations */}
          {hasObligations && (
            <div id="obligations-references" className="bg-white rounded-lg border border-slate-200 shadow-sm p-6 mb-6 scroll-mt-20">
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
                        className="block p-3 bg-sky-50 border border-sky-200 rounded-lg hover:border-sky-300 hover:shadow-sm transition-all"
                      >
                        <div className="flex items-center gap-2">
                          <span className="font-mono text-sm text-sky-600 font-medium">
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
                        className="block p-3 bg-sky-50 border border-sky-200 rounded-lg hover:border-sky-300 hover:shadow-sm transition-all"
                      >
                        <div className="flex items-center gap-2">
                          <span className="font-mono text-sm text-sky-600 font-medium">
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

            {/* Desktop Sidebar - Table of Contents */}
            <aside className="hidden lg:block lg:w-64 flex-shrink-0">
              <div className="sticky top-8">
                <div className="bg-white rounded-lg border border-slate-200 shadow-sm p-4">
                  <h3 className="text-sm font-semibold text-slate-900 mb-3">On This Page</h3>
                  <nav className="space-y-1">
                    {tocItems.map((item) => (
                      <a
                        key={item.id}
                        href={`#${item.id}`}
                        className="block px-3 py-2 text-sm text-slate-600 hover:text-teal-700 hover:bg-teal-50 rounded-md transition-colors"
                      >
                        {item.label}
                      </a>
                    ))}
                  </nav>
                </div>

                {/* Quick Stats */}
                <div className="bg-white rounded-lg border border-slate-200 shadow-sm p-4 mt-4">
                  <h3 className="text-sm font-semibold text-slate-900 mb-3">Quick Stats</h3>
                  <div className="space-y-2 text-sm">
                    {enhancedObligations.length > 0 && (
                      <div className="flex justify-between items-center">
                        <span className="text-slate-600">Obligations:</span>
                        <span className="font-medium text-slate-900">{enhancedObligations.length}</span>
                      </div>
                    )}
                    {deadlines.length > 0 && (
                      <div className="flex justify-between items-center">
                        <span className="text-slate-600">Deadlines:</span>
                        <span className="font-medium text-slate-900">{deadlines.length}</span>
                      </div>
                    )}
                    {amounts.length > 0 && (
                      <div className="flex justify-between items-center">
                        <span className="text-slate-600">Amounts:</span>
                        <span className="font-medium text-slate-900">{amounts.length}</span>
                      </div>
                    )}
                    {referencesFrom.length > 0 && (
                      <div className="flex justify-between items-center">
                        <span className="text-slate-600">Refs From:</span>
                        <span className="font-medium text-slate-900">{referencesFrom.length}</span>
                      </div>
                    )}
                    {referencesTo.length > 0 && (
                      <div className="flex justify-between items-center">
                        <span className="text-slate-600">Refs To:</span>
                        <span className="font-medium text-slate-900">{referencesTo.length}</span>
                      </div>
                    )}
                    {similarSections.length > 0 && (
                      <div className="flex justify-between items-center">
                        <span className="text-slate-600">Similar:</span>
                        <span className="font-medium text-slate-900">{similarSections.length}</span>
                      </div>
                    )}
                  </div>
                </div>
              </div>
            </aside>
          </div>
        </div>
      </div>
    </>
  );
}
