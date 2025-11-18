import { pgTable, text, boolean, jsonb, timestamp, bigserial, integer, bigint, real, index, primaryKey } from "drizzle-orm/pg-core";
import { sql } from "drizzle-orm";

/**
 * DC Code sections table
 */
export const dcSections = pgTable("dc_sections", {
  id: text("id").primaryKey(),
  citation: text("citation").notNull(),
  heading: text("heading").notNull(),
  textPlain: text("text_plain").notNull(),
  textHtml: text("text_html").notNull(),
  ancestors: jsonb("ancestors").notNull().default(sql`'[]'::jsonb`),
  titleLabel: text("title_label").notNull(),
  chapterLabel: text("chapter_label").notNull(),

  // Analysis fields
  hasReporting: boolean("has_reporting").default(false),
  reportingSummary: text("reporting_summary"),
  reportingTags: jsonb("reporting_tags").default(sql`'[]'::jsonb`),

  // Metadata
  createdAt: timestamp("created_at", { withTimezone: true }).defaultNow(),
  updatedAt: timestamp("updated_at", { withTimezone: true }).defaultNow(),
}, (table) => ({
  titleIdx: index("dc_sections_title_idx").on(table.titleLabel),
  chapterIdx: index("dc_sections_chapter_idx").on(table.chapterLabel),
  hasReportingIdx: index("dc_sections_has_reporting_idx").on(table.hasReporting),
}));

/**
 * Cross-references between sections
 */
export const dcSectionRefs = pgTable("dc_section_refs", {
  fromId: text("from_id").notNull().references(() => dcSections.id, { onDelete: "cascade" }),
  toId: text("to_id").notNull().references(() => dcSections.id, { onDelete: "cascade" }),
  rawCite: text("raw_cite").notNull(),
}, (table) => ({
  pk: primaryKey({ columns: [table.fromId, table.toId, table.rawCite] }),
  fromIdx: index("dc_section_refs_from_idx").on(table.fromId),
  toIdx: index("dc_section_refs_to_idx").on(table.toId),
}));

/**
 * Deadlines extracted from sections
 */
export const dcSectionDeadlines = pgTable("dc_section_deadlines", {
  id: bigserial("id", { mode: "number" }).primaryKey(),
  sectionId: text("section_id").notNull().references(() => dcSections.id, { onDelete: "cascade" }),
  phrase: text("phrase").notNull(),
  days: integer("days").notNull(),
  kind: text("kind").notNull(),
  createdAt: timestamp("created_at", { withTimezone: true }).defaultNow(),
}, (table) => ({
  sectionIdx: index("dc_section_deadlines_section_idx").on(table.sectionId),
  daysIdx: index("dc_section_deadlines_days_idx").on(table.days),
}));

/**
 * Dollar amounts extracted from sections
 */
export const dcSectionAmounts = pgTable("dc_section_amounts", {
  id: bigserial("id", { mode: "number" }).primaryKey(),
  sectionId: text("section_id").notNull().references(() => dcSections.id, { onDelete: "cascade" }),
  phrase: text("phrase").notNull(),
  amountCents: bigint("amount_cents", { mode: "number" }).notNull(),
  createdAt: timestamp("created_at", { withTimezone: true }).defaultNow(),
}, (table) => ({
  sectionIdx: index("dc_section_amounts_section_idx").on(table.sectionId),
  amountIdx: index("dc_section_amounts_amount_idx").on(table.amountCents),
}));

/**
 * Global tags for categorization
 */
export const dcGlobalTags = pgTable("dc_global_tags", {
  tag: text("tag").primaryKey(),
  createdAt: timestamp("created_at", { withTimezone: true }).defaultNow(),
});

/**
 * Section-to-tag mapping
 */
export const dcSectionTags = pgTable("dc_section_tags", {
  sectionId: text("section_id").notNull().references(() => dcSections.id, { onDelete: "cascade" }),
  tag: text("tag").notNull().references(() => dcGlobalTags.tag, { onDelete: "cascade" }),
}, (table) => ({
  pk: primaryKey({ columns: [table.sectionId, table.tag] }),
  sectionIdx: index("dc_section_tags_section_idx").on(table.sectionId),
  tagIdx: index("dc_section_tags_tag_idx").on(table.tag),
}));

/**
 * Similar sections (computed via embeddings)
 */
export const dcSectionSimilarities = pgTable("dc_section_similarities", {
  sectionA: text("section_a").notNull().references(() => dcSections.id, { onDelete: "cascade" }),
  sectionB: text("section_b").notNull().references(() => dcSections.id, { onDelete: "cascade" }),
  similarity: real("similarity").notNull(),
}, (table) => ({
  pk: primaryKey({ columns: [table.sectionA, table.sectionB] }),
  aIdx: index("dc_section_similarities_a_idx").on(table.sectionA, table.similarity),
  bIdx: index("dc_section_similarities_b_idx").on(table.sectionB, table.similarity),
}));

/**
 * Highlight phrases for reporting requirements
 */
export const dcSectionHighlights = pgTable("dc_section_highlights", {
  id: bigserial("id", { mode: "number" }).primaryKey(),
  sectionId: text("section_id").notNull().references(() => dcSections.id, { onDelete: "cascade" }),
  phrase: text("phrase").notNull(),
  createdAt: timestamp("created_at", { withTimezone: true }).defaultNow(),
}, (table) => ({
  sectionIdx: index("dc_section_highlights_section_idx").on(table.sectionId),
}));

/**
 * LLM-based classifications of similarity relationships
 */
export const dcSectionSimilarityClassifications = pgTable("dc_section_similarity_classifications", {
  sectionA: text("section_a").notNull(),
  sectionB: text("section_b").notNull(),
  classification: text("classification").notNull(),
  explanation: text("explanation").notNull(),
  modelUsed: text("model_used").notNull(),
  analyzedAt: timestamp("analyzed_at", { withTimezone: true }).notNull(),
  createdAt: timestamp("created_at", { withTimezone: true }).defaultNow(),
}, (table) => ({
  pk: primaryKey({ columns: [table.sectionA, table.sectionB] }),
  classificationIdx: index("dc_section_similarity_classifications_classification_idx").on(table.classification),
  modelIdx: index("dc_section_similarity_classifications_model_idx").on(table.modelUsed),
}));

// Type exports for use in application code
export type DcSection = typeof dcSections.$inferSelect;
export type NewDcSection = typeof dcSections.$inferInsert;

export type DcSectionRef = typeof dcSectionRefs.$inferSelect;
export type DcSectionDeadline = typeof dcSectionDeadlines.$inferSelect;
export type DcSectionAmount = typeof dcSectionAmounts.$inferSelect;
export type DcSectionSimilarity = typeof dcSectionSimilarities.$inferSelect;
export type DcSectionSimilarityClassification = typeof dcSectionSimilarityClassifications.$inferSelect;
