import { pgTable, text, boolean, jsonb, timestamp, bigserial, integer, bigint, real, index, primaryKey, varchar } from "drizzle-orm/pg-core";
import { sql } from "drizzle-orm";

/**
 * Jurisdictions metadata table
 */
export const jurisdictions = pgTable("jurisdictions", {
  id: varchar("id", { length: 10 }).primaryKey(),
  name: text("name").notNull(),
  abbreviation: varchar("abbreviation", { length: 10 }).notNull(),
  type: text("type").notNull(),
  parserVersion: text("parser_version").notNull(),
  createdAt: timestamp("created_at", { withTimezone: true }).defaultNow(),
});

/**
 * Code sections table (multi-jurisdiction)
 */
export const sections = pgTable("sections", {
  jurisdiction: varchar("jurisdiction", { length: 10 }).notNull().references(() => jurisdictions.id, { onDelete: "cascade" }),
  id: text("id").notNull(),
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
  reportingText: text("reporting_text"),
  reportingTags: jsonb("reporting_tags").default(sql`'[]'::jsonb`),

  // Metadata
  createdAt: timestamp("created_at", { withTimezone: true }).defaultNow(),
  updatedAt: timestamp("updated_at", { withTimezone: true }).defaultNow(),
}, (table) => ({
  pk: primaryKey({ columns: [table.jurisdiction, table.id] }),
  jurisdictionIdx: index("idx_sections_jurisdiction").on(table.jurisdiction),
  titleIdx: index("idx_sections_title").on(table.jurisdiction, table.titleLabel),
  chapterIdx: index("idx_sections_chapter").on(table.jurisdiction, table.chapterLabel),
  hasReportingIdx: index("idx_sections_has_reporting").on(table.jurisdiction, table.hasReporting),
}));

/**
 * Cross-references between sections
 */
export const sectionRefs = pgTable("section_refs", {
  jurisdiction: varchar("jurisdiction", { length: 10 }).notNull(),
  fromId: text("from_id").notNull(),
  toId: text("to_id").notNull(),
  rawCite: text("raw_cite").notNull(),
}, (table) => ({
  pk: primaryKey({ columns: [table.jurisdiction, table.fromId, table.toId, table.rawCite] }),
  fromIdx: index("idx_section_refs_from").on(table.jurisdiction, table.fromId),
  toIdx: index("idx_section_refs_to").on(table.jurisdiction, table.toId),
}));

/**
 * Deadlines extracted from sections
 */
export const sectionDeadlines = pgTable("section_deadlines", {
  id: bigserial("id", { mode: "number" }),
  jurisdiction: varchar("jurisdiction", { length: 10 }).notNull(),
  sectionId: text("section_id").notNull(),
  phrase: text("phrase").notNull(),
  days: integer("days").notNull(),
  kind: text("kind").notNull(),
  createdAt: timestamp("created_at", { withTimezone: true }).defaultNow(),
}, (table) => ({
  pk: primaryKey({ columns: [table.jurisdiction, table.id] }),
  sectionIdx: index("idx_section_deadlines_section").on(table.jurisdiction, table.sectionId),
  daysIdx: index("idx_section_deadlines_days").on(table.days),
}));

/**
 * Dollar amounts extracted from sections
 */
export const sectionAmounts = pgTable("section_amounts", {
  id: bigserial("id", { mode: "number" }),
  jurisdiction: varchar("jurisdiction", { length: 10 }).notNull(),
  sectionId: text("section_id").notNull(),
  phrase: text("phrase").notNull(),
  amountCents: bigint("amount_cents", { mode: "number" }).notNull(),
  createdAt: timestamp("created_at", { withTimezone: true }).defaultNow(),
}, (table) => ({
  pk: primaryKey({ columns: [table.jurisdiction, table.id] }),
  sectionIdx: index("idx_section_amounts_section").on(table.jurisdiction, table.sectionId),
  amountIdx: index("idx_section_amounts_amount").on(table.amountCents),
}));

/**
 * Enhanced obligations extracted from sections using LLM analysis
 * Replaces/extends deadlines and amounts with categorized obligations
 */
export const obligations = pgTable("obligations", {
  id: bigserial("id", { mode: "number" }),
  jurisdiction: varchar("jurisdiction", { length: 10 }).notNull(),
  sectionId: text("section_id").notNull(),
  category: text("category").notNull(), // deadline, amount, reporting, constraint, penalty, allocation, other
  phrase: text("phrase").notNull(),
  value: real("value"), // Extracted numeric value (nullable)
  unit: text("unit"), // Unit of measurement (days, dollars, years, etc.)
  confidence: real("confidence"), // LLM confidence score (0.0-1.0)
  createdAt: timestamp("created_at", { withTimezone: true }).defaultNow(),
}, (table) => ({
  pk: primaryKey({ columns: [table.jurisdiction, table.id] }),
  sectionIdx: index("idx_obligations_section").on(table.jurisdiction, table.sectionId),
  categoryIdx: index("idx_obligations_category").on(table.jurisdiction, table.category),
}));

/**
 * Global tags for categorization (jurisdiction-agnostic)
 */
export const globalTags = pgTable("global_tags", {
  tag: text("tag").primaryKey(),
  createdAt: timestamp("created_at", { withTimezone: true }).defaultNow(),
});

/**
 * Section-to-tag mapping
 */
export const sectionTags = pgTable("section_tags", {
  jurisdiction: varchar("jurisdiction", { length: 10 }).notNull(),
  sectionId: text("section_id").notNull(),
  tag: text("tag").notNull().references(() => globalTags.tag, { onDelete: "cascade" }),
}, (table) => ({
  pk: primaryKey({ columns: [table.jurisdiction, table.sectionId, table.tag] }),
  sectionIdx: index("idx_section_tags_section").on(table.jurisdiction, table.sectionId),
  tagIdx: index("idx_section_tags_tag").on(table.tag),
}));

/**
 * Similar sections (computed via embeddings)
 */
export const sectionSimilarities = pgTable("section_similarities", {
  jurisdiction: varchar("jurisdiction", { length: 10 }).notNull(),
  sectionA: text("section_a").notNull(),
  sectionB: text("section_b").notNull(),
  similarity: real("similarity").notNull(),
}, (table) => ({
  pk: primaryKey({ columns: [table.jurisdiction, table.sectionA, table.sectionB] }),
  aIdx: index("idx_section_similarities_a").on(table.jurisdiction, table.sectionA, table.similarity),
  bIdx: index("idx_section_similarities_b").on(table.jurisdiction, table.sectionB, table.similarity),
}));

/**
 * Highlight phrases for reporting requirements
 */
export const sectionHighlights = pgTable("section_highlights", {
  id: bigserial("id", { mode: "number" }),
  jurisdiction: varchar("jurisdiction", { length: 10 }).notNull(),
  sectionId: text("section_id").notNull(),
  phrase: text("phrase").notNull(),
  createdAt: timestamp("created_at", { withTimezone: true }).defaultNow(),
}, (table) => ({
  pk: primaryKey({ columns: [table.jurisdiction, table.id] }),
  sectionIdx: index("idx_section_highlights_section").on(table.jurisdiction, table.sectionId),
}));

/**
 * LLM-based classifications of similarity relationships
 */
export const sectionSimilarityClassifications = pgTable("section_similarity_classifications", {
  jurisdiction: varchar("jurisdiction", { length: 10 }).notNull(),
  sectionA: text("section_a").notNull(),
  sectionB: text("section_b").notNull(),
  classification: text("classification").notNull(),
  explanation: text("explanation").notNull(),
  modelUsed: text("model_used").notNull(),
  analyzedAt: timestamp("analyzed_at", { withTimezone: true }).notNull(),
  createdAt: timestamp("created_at", { withTimezone: true }).defaultNow(),
}, (table) => ({
  pk: primaryKey({ columns: [table.jurisdiction, table.sectionA, table.sectionB] }),
  classificationIdx: index("idx_section_similarity_classifications_classification").on(table.jurisdiction, table.classification),
  modelIdx: index("idx_section_similarity_classifications_model").on(table.modelUsed),
}));

/**
 * Hierarchical structure table for legal code organization
 */
export const structure = pgTable("structure", {
  jurisdiction: varchar("jurisdiction", { length: 10 }).notNull().references(() => jurisdictions.id, { onDelete: "cascade" }),
  id: text("id").notNull(),
  parentId: text("parent_id"),
  level: text("level").notNull(), // 'title', 'subtitle', 'chapter', 'subchapter', 'section'
  label: text("label").notNull(),
  heading: text("heading"),
  ordinal: integer("ordinal"),
  createdAt: timestamp("created_at", { withTimezone: true }).defaultNow(),
}, (table) => ({
  pk: primaryKey({ columns: [table.jurisdiction, table.id] }),
  jurisdictionIdx: index("idx_structure_jurisdiction").on(table.jurisdiction),
  parentIdx: index("idx_structure_parent").on(table.jurisdiction, table.parentId),
  levelIdx: index("idx_structure_level").on(table.jurisdiction, table.level),
  ordinalIdx: index("idx_structure_ordinal").on(table.jurisdiction, table.ordinal),
}));

// Type exports for use in application code
export type Jurisdiction = typeof jurisdictions.$inferSelect;
export type NewJurisdiction = typeof jurisdictions.$inferInsert;

export type Section = typeof sections.$inferSelect;
export type NewSection = typeof sections.$inferInsert;

export type SectionRef = typeof sectionRefs.$inferSelect;
export type SectionDeadline = typeof sectionDeadlines.$inferSelect;
export type SectionAmount = typeof sectionAmounts.$inferSelect;
export type SectionSimilarity = typeof sectionSimilarities.$inferSelect;
export type SectionSimilarityClassification = typeof sectionSimilarityClassifications.$inferSelect;
export type SectionHighlight = typeof sectionHighlights.$inferSelect;
export type SectionTag = typeof sectionTags.$inferSelect;
export type GlobalTag = typeof globalTags.$inferSelect;
export type Structure = typeof structure.$inferSelect;
