# Deproceduralizer Design System

A modern, sophisticated design system for legal code documentation and analysis.

## Design Principles

1. **Professional & Trustworthy**: Legal documentation requires a serious, credible aesthetic
2. **Readable & Accessible**: WCAG 2.2 AA compliance minimum, optimized for long-form reading
3. **Modern & Clean**: Contemporary design that feels current, not dated
4. **Hierarchical & Organized**: Clear visual hierarchy to navigate complex legal information

---

## Color Palette

### Primary Colors

Our primary palette uses sophisticated slate blues that convey professionalism and trust.

| Color | Tailwind | Hex | Usage |
|-------|----------|-----|-------|
| **Slate 50** | `slate-50` | `#f8fafc` | Backgrounds, subtle panels |
| **Slate 100** | `slate-100` | `#f1f5f9` | Secondary backgrounds |
| **Slate 200** | `slate-200` | `#e2e8f0` | Borders, dividers |
| **Slate 300** | `slate-300` | `#cbd5e1` | Disabled states |
| **Slate 600** | `slate-600` | `#475569` | Secondary text |
| **Slate 700** | `slate-700` | `#334155` | **PRIMARY** - Main brand color, headings |
| **Slate 800** | `slate-800` | `#1e293b` | Body text |
| **Slate 900** | `slate-900` | `#0f172a` | Emphasis text |

### Secondary Colors

Deep teal provides a modern, trustworthy accent that pairs well with slate.

| Color | Tailwind | Hex | Usage |
|-------|----------|-----|-------|
| **Teal 50** | `teal-50` | `#f0fdfa` | Success backgrounds |
| **Teal 600** | `teal-600` | `#0d9488` | Secondary actions, links |
| **Teal 700** | `teal-700` | `#0f766e` | **SECONDARY** - CTAs, interactive elements |
| **Teal 800** | `teal-800` | `#115e59` | Hover states |

### Accent Colors

Refined amber provides warmth and draws attention to key actions.

| Color | Tailwind | Hex | Usage |
|-------|----------|-----|-------|
| **Amber 50** | `amber-50` | `#fffbeb` | Warning backgrounds |
| **Amber 400** | `amber-400` | `#fbbf24` | Highlights, emphasis |
| **Amber 500** | `amber-500` | `#f59e0b` | **ACCENT** - CTAs, highlights |
| **Amber 600** | `amber-600` | `#d97706` | Hover states |

### Semantic Colors

Purpose-specific colors for data visualization and status communication.

#### Deadlines & Time Requirements
```css
Background: amber-50  (#fffbeb)
Border: amber-200     (#fde68a)
Badge: amber-600      (#d97706)
Text: amber-900       (#78350f)
```

#### Dollar Amounts
```css
Background: emerald-50  (#ecfdf5)
Border: emerald-200     (#a7f3d0)
Badge: emerald-600      (#059669)
Text: emerald-900       (#064e3b)
```

#### Reporting Requirements
```css
Background: violet-50  (#f5f3ff)
Border: violet-200     (#ddd6fe)
Badge: violet-600      (#7c3aed)
Text: violet-900       (#4c1d95)
```

#### Similar Sections
```css
Background: sky-50  (#f0f9ff)
Border: sky-200     (#bae6fd)
Badge: sky-600      (#0284c7)
Text: sky-900       (#0c4a6e)
```

#### Cross-References (From)
```css
Background: blue-50  (#eff6ff)
Border: blue-200     (#bfdbfe)
Badge: blue-600      (#2563eb)
Text: blue-900       (#1e3a8a)
```

#### Cross-References (To)
```css
Background: indigo-50  (#eef2ff)
Border: indigo-200     (#c7d2fe)
Badge: indigo-600      (#4f46e5)
Text: indigo-900       (#312e81)
```

#### Diff Viewer Colors
```css
/* Unified View */
Removed: bg-red-50      text-red-900      (strikethrough)
Added: bg-green-50      text-green-900
Unchanged: text-slate-700

/* Split View */
Left (current): bg-slate-50
Right (comparison): bg-slate-100
```

#### Status Colors
```css
Success: emerald-600   (#059669)
Warning: amber-600     (#d97706)
Error: red-600         (#dc2626)
Info: sky-600          (#0284c7)
```

---

## Typography

### Font Stack

```css
/* System font stack for optimal performance and native feel */
font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto,
             "Helvetica Neue", Arial, sans-serif;

/* Monospace for code, citations */
font-family: ui-monospace, SFMono-Regular, "SF Mono", Menlo, Monaco,
             Consolas, "Liberation Mono", "Courier New", monospace;
```

### Type Scale

| Usage | Class | Size | Line Height | Weight |
|-------|-------|------|-------------|--------|
| **Hero Title** | `text-5xl` | 48px / 3rem | 1 | 700 (bold) |
| **Page Title** | `text-4xl` | 36px / 2.25rem | 1.1 | 700 (bold) |
| **Section Heading** | `text-3xl` | 30px / 1.875rem | 1.2 | 700 (bold) |
| **Subsection** | `text-2xl` | 24px / 1.5rem | 1.33 | 600 (semibold) |
| **Card Heading** | `text-xl` | 20px / 1.25rem | 1.4 | 600 (semibold) |
| **Large Body** | `text-lg` | 18px / 1.125rem | 1.556 | 400 (normal) |
| **Body Text** | `text-base` | 16px / 1rem | 1.625 | 400 (normal) |
| **Small Text** | `text-sm` | 14px / 0.875rem | 1.429 | 400 (normal) |
| **Tiny Text** | `text-xs` | 12px / 0.75rem | 1.333 | 400 (normal) |

### Typography Guidelines

#### Headings
```tsx
// Page-level headings
<h1 className="text-4xl font-bold text-slate-900">

// Section headings
<h2 className="text-2xl font-semibold text-slate-900">

// Subsection headings
<h3 className="text-xl font-semibold text-slate-800">
```

#### Body Text
```tsx
// Primary body text
<p className="text-base text-slate-700 leading-relaxed">

// Secondary/muted text
<p className="text-sm text-slate-600">

// Fine print
<p className="text-xs text-slate-500">
```

#### Legal Citations
```tsx
// Monospace for citations
<span className="font-mono text-sm text-teal-700 font-medium">
```

---

## Spacing & Layout

### Spacing Scale

Follow Tailwind's default spacing scale (4px base):

| Token | px | Usage |
|-------|-------|-------|
| `0.5` | 2px | Tight inline spacing |
| `1` | 4px | Very tight spacing |
| `2` | 8px | Compact spacing |
| `3` | 12px | Default inline spacing |
| `4` | 16px | Standard spacing |
| `6` | 24px | Relaxed spacing |
| `8` | 32px | Loose spacing |
| `12` | 48px | Section spacing |
| `16` | 64px | Major section spacing |
| `20` | 80px | Page-level spacing |

### Container Widths

```css
/* Page containers */
max-w-7xl    /* 1280px - Default page width */
max-w-5xl    /* 1024px - Centered content */
max-w-4xl    /* 896px - Reading-optimized width for section detail */
max-w-2xl    /* 672px - Forms, narrow content */
```

### Grid Layouts

```tsx
// 3-column feature grid
<div className="grid md:grid-cols-3 gap-6">

// 2-column comparison
<div className="grid grid-cols-2 gap-4">

// Responsive card grid
<div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
```

---

## Components

### Buttons

#### Primary Button
```tsx
<button className="px-6 py-3 bg-teal-700 text-white rounded-lg hover:bg-teal-800
                   font-medium shadow-sm transition-colors">
  Primary Action
</button>
```

#### Secondary Button
```tsx
<button className="px-6 py-3 bg-slate-100 text-slate-700 rounded-lg hover:bg-slate-200
                   font-medium border border-slate-300 transition-colors">
  Secondary Action
</button>
```

#### Ghost Button
```tsx
<button className="px-4 py-2 text-teal-700 hover:bg-teal-50 rounded-lg
                   font-medium transition-colors">
  Subtle Action
</button>
```

#### Destructive Button
```tsx
<button className="px-6 py-3 bg-red-600 text-white rounded-lg hover:bg-red-700
                   font-medium shadow-sm transition-colors">
  Delete
</button>
```

#### Small Button
```tsx
<button className="px-3 py-1.5 text-xs bg-teal-700 text-white rounded
                   hover:bg-teal-800 font-medium transition-colors">
  Small Action
</button>
```

### Cards & Panels

#### Standard Card
```tsx
<div className="bg-white rounded-lg border border-slate-200 shadow-sm p-6">
  {/* Content */}
</div>
```

#### Elevated Card
```tsx
<div className="bg-white rounded-xl border border-slate-200 shadow-md p-6
                hover:shadow-lg transition-shadow">
  {/* Content */}
</div>
```

#### Colored Panel (for obligations)
```tsx
// Deadline panel
<div className="p-4 bg-amber-50 border border-amber-200 rounded-lg">

// Amount panel
<div className="p-4 bg-emerald-50 border border-emerald-200 rounded-lg">

// Reporting panel
<div className="p-4 bg-violet-50 border border-violet-200 rounded-lg">
```

### Badges

#### Status Badges
```tsx
// Success
<span className="px-2 py-0.5 bg-emerald-100 text-emerald-800 text-xs
               font-semibold rounded-full">
  Active
</span>

// Info
<span className="px-2 py-0.5 bg-sky-100 text-sky-800 text-xs
               font-semibold rounded-full">
  100% match
</span>

// Warning
<span className="px-2 py-0.5 bg-amber-100 text-amber-800 text-xs
               font-semibold rounded-full">
  Pending
</span>
```

#### Feature Badges
```tsx
// Deadlines
<span className="px-3 py-1 bg-amber-600 text-white text-sm
               font-semibold rounded-full">
  30 days
</span>

// Amounts
<span className="px-3 py-1 bg-emerald-600 text-white text-sm
               font-semibold rounded-full font-mono">
  $1,000.00
</span>
```

### Forms & Inputs

#### Text Input
```tsx
<input
  type="text"
  className="px-4 py-3 border border-slate-300 rounded-lg
             focus:outline-none focus:ring-2 focus:ring-teal-500 focus:border-transparent
             text-slate-900 placeholder:text-slate-400"
  placeholder="Enter search term..."
/>
```

#### Select Dropdown
```tsx
<select className="px-4 py-3 border border-slate-300 rounded-lg
                   focus:outline-none focus:ring-2 focus:ring-teal-500
                   text-slate-900 bg-white">
  <option>Select option</option>
</select>
```

#### Checkbox
```tsx
<input
  type="checkbox"
  className="h-4 w-4 text-teal-700 focus:ring-teal-500
             border-slate-300 rounded"
/>
```

### Links

#### Primary Link
```tsx
<Link href="/" className="text-teal-700 hover:text-teal-800 font-medium
                         underline decoration-2 underline-offset-2">
  View Details
</Link>
```

#### Subtle Link
```tsx
<Link href="/" className="text-teal-700 hover:text-teal-800">
  Learn more →
</Link>
```

#### Navigation Link
```tsx
<Link href="/" className="text-slate-700 hover:text-slate-900
                         font-medium transition-colors">
  Search
</Link>
```

### Navigation

#### Two-Tier Navigation System

Our navigation uses a two-tier architecture: primary navigation for main sections, and contextual secondary navigation for related pages within a section.

**Primary Navigation** (always visible):
```tsx
<nav className="bg-white border-b border-slate-200 shadow-sm">
  <div className="max-w-7xl mx-auto px-4 py-4">
    <div className="flex items-center justify-between">
      <Link href="/" className="text-xl font-bold text-slate-900 hover:text-teal-700">
        Deproceduralizer
      </Link>
      <div className="flex gap-6">
        <Link href="/search" className="font-medium text-slate-700 hover:text-slate-900">
          Search
        </Link>
        <Link href="/browse" className="font-medium text-slate-700 hover:text-slate-900">
          Browse
        </Link>
        <Link href="/dashboard/conflicts" className="font-medium text-slate-700 hover:text-slate-900">
          Analysis
        </Link>
      </div>
    </div>
  </div>
</nav>
```

**Secondary Navigation** (contextual, shown for Analysis section):
```tsx
{/* Only shown on /dashboard/conflicts, /reporting, /anachronisms, /pahlka-implementations */}
<div className="bg-slate-50 border-b border-slate-200">
  <div className="max-w-7xl mx-auto px-4 py-3">
    <div className="flex items-center gap-6 text-sm">
      <Link href="/dashboard/conflicts"
            className="font-medium text-teal-700 border-b-2 border-teal-700 pb-1">
        Conflicts
      </Link>
      <Link href="/reporting"
            className="font-medium text-slate-600 hover:text-slate-900">
        Reporting
      </Link>
      <Link href="/anachronisms"
            className="font-medium text-slate-600 hover:text-slate-900">
        Anachronisms
      </Link>
      <Link href="/pahlka-implementations"
            className="font-medium text-slate-600 hover:text-slate-900">
        Implementation
      </Link>
    </div>
  </div>
</div>
```

**Breadcrumbs** (shown when not in Analysis section):
```tsx
<div className="bg-slate-50 border-b border-slate-200">
  <div className="max-w-7xl mx-auto px-4 py-3">
    <div className="flex items-center gap-2 text-sm text-slate-600">
      <Link href="/" className="hover:text-slate-900">Home</Link>
      <span>›</span>
      <Link href="/search" className="hover:text-slate-900">Search</Link>
      <span>›</span>
      <span className="text-slate-900 font-medium">Results</span>
    </div>
  </div>
</div>
```

---

## Page Layouts

### Hero Section (Home Page)

Modern, spacious hero with enhanced gradients and prominent search:

```tsx
<div className="min-h-screen bg-gradient-to-br from-slate-50 via-white to-teal-50/30">
  {/* Sticky Header */}
  <header className="border-b border-slate-200/50 bg-white/80 backdrop-blur-sm sticky top-0 z-10">
    <div className="max-w-7xl mx-auto px-4 py-4 flex items-center justify-between">
      <Link href="/" className="text-lg font-bold text-slate-900 hover:text-teal-700">
        Deproceduralizer
      </Link>
      <div className="flex gap-6">
        <Link href="/search" className="text-sm font-medium text-slate-600 hover:text-slate-900">
          Search
        </Link>
        <Link href="/browse" className="text-sm font-medium text-slate-600 hover:text-slate-900">
          Browse
        </Link>
        <Link href="/dashboard/conflicts" className="text-sm font-medium text-slate-600 hover:text-slate-900">
          Analysis
        </Link>
      </div>
    </div>
  </header>

  {/* Hero */}
  <div className="max-w-6xl mx-auto px-4 py-20 md:py-32">
    <div className="text-center mb-12">
      <h1 className="text-6xl md:text-7xl lg:text-8xl font-bold text-slate-900 mb-6 tracking-tight leading-none">
        Deproceduralizer
      </h1>
      <p className="text-2xl md:text-3xl text-slate-600 mb-4 font-light">
        Search and analyze Washington, D.C. legal code
      </p>
      <p className="text-base text-slate-500">
        Full-text search • Cross-references • Obligations tracking
      </p>
    </div>

    {/* Enhanced Search Bar */}
    <div className="max-w-4xl mx-auto mb-24">
      <form className="relative">
        <div className="flex gap-3 shadow-xl rounded-xl overflow-hidden border border-slate-200 bg-white">
          <input
            type="text"
            placeholder="Search DC Code..."
            className="flex-1 px-6 py-6 text-lg focus:outline-none text-slate-900 placeholder:text-slate-400 bg-white"
          />
          <button className="px-12 py-6 bg-teal-700 text-white hover:bg-teal-800 font-semibold text-lg">
            Search
          </button>
        </div>
      </form>
    </div>
  </div>
</div>
```

### Content Page
```tsx
<div className="min-h-screen bg-slate-50">
  <div className="max-w-7xl mx-auto px-4 py-8">
    {/* Content */}
  </div>
</div>
```

### Section Detail Page
```tsx
<div className="min-h-screen bg-slate-50">
  <div className="max-w-4xl mx-auto px-4 py-8">
    {/* Optimized reading width for legal text */}
  </div>
</div>
```

---

## Usage Examples

### Search Results Card
```tsx
<Link href={`/section/${result.id}`}
      className="block bg-white rounded-lg border border-slate-200 p-5
                 hover:border-teal-300 hover:shadow-md transition-all">
  {/* Breadcrumbs */}
  <div className="text-xs text-slate-500 mb-2">
    <span>{result.titleLabel}</span>
    <span className="mx-1.5">›</span>
    <span>{result.chapterLabel}</span>
  </div>

  {/* Citation */}
  <div className="font-mono text-sm text-teal-700 font-medium mb-2">
    {result.citation}
  </div>

  {/* Heading */}
  <h3 className="text-lg font-semibold text-slate-900 mb-2">
    {result.heading}
  </h3>

  {/* Snippet */}
  <p className="text-sm text-slate-600 line-clamp-2">
    {result.snippet}
  </p>
</Link>
```

### Obligation Card
```tsx
<div className="p-4 bg-amber-50 border border-amber-200 rounded-lg">
  <div className="flex gap-3">
    <span className="flex-shrink-0 px-3 py-1 bg-amber-600 text-white
                     text-sm font-semibold rounded-full">
      30 days
    </span>
    <p className="text-slate-700 text-sm">
      ...within thirty days after receipt of the application...
    </p>
  </div>
</div>
```

---

## Accessibility Guidelines

### Color Contrast
- All text must meet WCAG 2.2 AA standards (4.5:1 for normal text, 3:1 for large text)
- Interactive elements must have clear focus states
- Never rely on color alone to convey information

### Focus States
```tsx
// Always include focus rings
focus:outline-none focus:ring-2 focus:ring-teal-500 focus:ring-offset-2
```

### Alt Text & ARIA
- All images must have descriptive alt text
- Use semantic HTML (`<nav>`, `<main>`, `<article>`, etc.)
- Add ARIA labels where helpful but don't over-use

---

## Responsive Design

### Breakpoints
```css
sm:  640px   /* Small tablets */
md:  768px   /* Tablets */
lg:  1024px  /* Laptops */
xl:  1280px  /* Desktops */
2xl: 1536px  /* Large desktops */
```

### Mobile-First Approach
Always start with mobile styles and scale up:
```tsx
className="text-sm md:text-base lg:text-lg"
className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3"
className="p-4 md:p-6 lg:p-8"
```

---

## Animation & Transitions

### Hover Transitions
```css
transition-colors    /* For color changes */
transition-shadow    /* For shadow changes */
transition-all       /* For multiple properties (use sparingly) */
```

### Loading States
```tsx
// Spinner
<div className="inline-block animate-spin rounded-full h-6 w-6
                border-2 border-teal-600 border-t-transparent" />

// Pulse (for skeleton loaders)
<div className="animate-pulse bg-slate-200 h-4 rounded" />
```

---

## Migration Checklist

When updating existing components:

- [ ] Replace `blue-*` classes with `teal-*` or `slate-*` as appropriate
- [ ] Replace `indigo-*` with `sky-*` for similar sections
- [ ] Replace `purple-*` with `violet-*` for reporting
- [ ] Update button styles to match new design
- [ ] Add proper focus states to interactive elements
- [ ] Verify color contrast ratios
- [ ] Test responsive layouts on mobile
- [ ] Add/update breadcrumbs where appropriate
- [ ] Ensure consistent spacing using scale
- [ ] Update card shadows to `shadow-sm` or `shadow-md`

---

## Footer Component

Comprehensive footer with 4-column grid layout:

```tsx
<footer className="bg-slate-900 text-slate-300 mt-20">
  <div className="max-w-7xl mx-auto px-4 py-12">
    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-8 mb-8">
      {/* About Column */}
      <div>
        <h3 className="text-white font-semibold text-lg mb-4">
          Deproceduralizer
        </h3>
        <p className="text-sm text-slate-400 mb-4">
          A modern tool for searching and analyzing Washington, D.C. legal code
        </p>
        <p className="text-xs text-slate-500">Version 0.1.0</p>
      </div>

      {/* Navigation Column */}
      <div>
        <h4 className="text-white font-semibold mb-4">Navigate</h4>
        <ul className="space-y-2 text-sm">
          <li><Link href="/search" className="hover:text-teal-400">Search</Link></li>
          <li><Link href="/browse" className="hover:text-teal-400">Browse Code</Link></li>
          <li><Link href="/reporting" className="hover:text-teal-400">Reporting Requirements</Link></li>
        </ul>
      </div>

      {/* Resources Column */}
      <div>
        <h4 className="text-white font-semibold mb-4">Resources</h4>
        <ul className="space-y-2 text-sm">
          <li><a href="https://github.com/DCCouncil/law-xml" className="hover:text-teal-400">DC Law XML</a></li>
          <li><Link href="/pahlka-implementations" className="hover:text-teal-400">Implementation Analysis</Link></li>
        </ul>
      </div>

      {/* Information Column */}
      <div>
        <h4 className="text-white font-semibold mb-4">Information</h4>
        <p className="text-sm text-slate-400">Data sourced from the official DC Code XML repository</p>
      </div>
    </div>

    {/* Bottom Bar */}
    <div className="border-t border-slate-800 pt-8 flex justify-between items-center">
      <div className="text-sm text-slate-500">
        © {currentYear} Deproceduralizer. All rights reserved.
      </div>
      <div className="text-sm text-slate-500">
        Powered by <a href="https://nextjs.org" className="hover:text-teal-400">Next.js</a>
        {" + "}
        <a href="https://www.postgresql.org" className="hover:text-teal-400">PostgreSQL</a>
      </div>
    </div>
  </div>
</footer>
```

**Usage:**
- Add Footer component to layout.tsx wrapped in flex-col min-h-screen
- Main content should use flex-grow class to push footer to bottom

---

*Last updated: 2025-11-20*
