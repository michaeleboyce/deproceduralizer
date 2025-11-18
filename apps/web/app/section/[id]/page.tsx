import { notFound } from "next/navigation";
import Link from "next/link";
import { db } from "@/lib/db";
import {
  dcSections,
  dcSectionDeadlines,
  dcSectionAmounts,
  dcSectionRefs,
  dcSectionSimilarities,
} from "@/db/schema";
import { eq, or, and, sql } from "drizzle-orm";
import SimilarSectionsList from "@/components/SimilarSectionsList";

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
  // Note: Currently 0 due to FK constraints with subset data
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

  // Fetch similar sections (both directions: section_a and section_b)
  const similarFromA = await db
    .select({
      id: dcSections.id,
      citation: dcSections.citation,
      heading: dcSections.heading,
      similarity: dcSectionSimilarities.similarity,
    })
    .from(dcSectionSimilarities)
    .innerJoin(dcSections, eq(dcSectionSimilarities.sectionB, dcSections.id))
    .where(eq(dcSectionSimilarities.sectionA, id))
    .orderBy(sql`${dcSectionSimilarities.similarity} DESC`)
    .limit(5);

  const similarFromB = await db
    .select({
      id: dcSections.id,
      citation: dcSections.citation,
      heading: dcSections.heading,
      similarity: dcSectionSimilarities.similarity,
    })
    .from(dcSectionSimilarities)
    .innerJoin(dcSections, eq(dcSectionSimilarities.sectionA, dcSections.id))
    .where(eq(dcSectionSimilarities.sectionB, id))
    .orderBy(sql`${dcSectionSimilarities.similarity} DESC`)
    .limit(5);

  // Combine and sort similar sections
  const similarSections = [...similarFromA, ...similarFromB]
    .sort((a, b) => b.similarity - a.similarity)
    .slice(0, 5);

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
    <div className="min-h-screen bg-gray-50 py-8 px-4">
      <div className="max-w-4xl mx-auto">
        {/* Back Link */}
        <Link
          href="/search"
          className="inline-flex items-center gap-1 text-blue-600 hover:text-blue-700 mb-4 font-medium"
        >
          ← Back to Search
        </Link>

        {/* Header */}
        <div className="bg-white rounded-lg border border-gray-200 p-6 mb-6">
          {/* Breadcrumbs */}
          <div className="text-sm text-gray-500 mb-3">
            <span>{section.titleLabel}</span>
            <span className="mx-2">›</span>
            <span>{section.chapterLabel}</span>
            <span className="mx-2">›</span>
            <span className="font-mono text-blue-600">{section.citation}</span>
          </div>

          {/* Heading */}
          <h1 className="text-3xl font-bold text-gray-900 mb-4">
            {section.heading}
          </h1>

          {/* Citation */}
          <div className="text-gray-600">
            <span className="font-semibold">Citation:</span>{" "}
            <span className="font-mono">{section.citation}</span>
          </div>
        </div>

        {/* Main Content */}
        <div className="bg-white rounded-lg border border-gray-200 p-6 mb-6">
          <h2 className="text-xl font-semibold text-gray-900 mb-4">
            Section Text
          </h2>
          <div
            className="prose prose-sm max-w-none text-gray-700 leading-relaxed"
            dangerouslySetInnerHTML={{ __html: section.textHtml }}
          />
        </div>

        {/* Obligations */}
        {hasObligations && (
          <div className="bg-white rounded-lg border border-gray-200 p-6 mb-6">
            <h2 className="text-xl font-semibold text-gray-900 mb-4">
              Obligations & References
            </h2>

            {/* Deadlines */}
            {deadlines.length > 0 && (
              <div className="mb-6">
                <h3 className="text-lg font-medium text-gray-800 mb-3">
                  Deadlines & Time Requirements ({deadlines.length})
                </h3>
                <div className="space-y-3">
                  {deadlines.map((deadline, index) => (
                    <div
                      key={index}
                      className="flex gap-3 p-3 bg-amber-50 border border-amber-200 rounded-lg"
                    >
                      <div className="flex-shrink-0">
                        <span className="inline-block px-3 py-1 bg-amber-600 text-white text-sm font-semibold rounded-full">
                          {deadline.days} day{deadline.days !== 1 ? "s" : ""}
                        </span>
                      </div>
                      <div className="flex-1">
                        <p className="text-gray-700 text-sm line-clamp-2">
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
                <h3 className="text-lg font-medium text-gray-800 mb-3">
                  Dollar Amounts ({amounts.length})
                </h3>
                <div className="space-y-3">
                  {amounts.map((amount, index) => (
                    <div
                      key={index}
                      className="flex gap-3 p-3 bg-green-50 border border-green-200 rounded-lg"
                    >
                      <div className="flex-shrink-0">
                        <span className="inline-block px-3 py-1 bg-green-600 text-white text-sm font-semibold rounded-full font-mono">
                          {formatCurrency(amount.amountCents)}
                        </span>
                      </div>
                      <div className="flex-1">
                        <p className="text-gray-700 text-sm line-clamp-2">
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
                <h3 className="text-lg font-medium text-gray-800 mb-3">
                  References From This Section ({referencesFrom.length})
                </h3>
                <div className="space-y-2">
                  {referencesFrom.map((ref, index) => (
                    <Link
                      key={index}
                      href={`/section/${ref.id}`}
                      className="block p-3 bg-blue-50 border border-blue-200 rounded-lg hover:bg-blue-100 transition-colors"
                    >
                      <div className="flex items-center gap-2">
                        <span className="font-mono text-sm text-blue-600 font-medium">
                          {ref.citation}
                        </span>
                        <span className="text-gray-600">→</span>
                        <span className="text-gray-700 text-sm">
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
                <h3 className="text-lg font-medium text-gray-800 mb-3">
                  References To This Section ({referencesTo.length})
                </h3>
                <div className="space-y-2">
                  {referencesTo.map((ref, index) => (
                    <Link
                      key={index}
                      href={`/section/${ref.id}`}
                      className="block p-3 bg-purple-50 border border-purple-200 rounded-lg hover:bg-purple-100 transition-colors"
                    >
                      <div className="flex items-center gap-2">
                        <span className="font-mono text-sm text-purple-600 font-medium">
                          {ref.citation}
                        </span>
                        <span className="text-gray-600">←</span>
                        <span className="text-gray-700 text-sm">
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

        {/* Similar Sections */}
        <SimilarSectionsList
          currentSectionId={id}
          currentSectionCitation={section.citation}
          similarSections={similarSections}
        />

        {/* Empty State */}
        {!hasObligations && (
          <div className="bg-white rounded-lg border border-gray-200 p-6 text-center">
            <p className="text-gray-500">
              No deadlines, dollar amounts, or cross-references found in this
              section.
            </p>
          </div>
        )}
      </div>
    </div>
  );
}
