<!-- SEED: established with the user before implementation; re-run /impeccable document once the report viewer has real code, to capture the actual tokens and components as built. -->

---
name: Hallucination / Factual-Consistency Scorer — Report Viewer
description: A dark, terminal-adjacent evidence docket for a claim-level fact-checking pipeline.
colors:
  ink: "#0A0C0F"
  surface: "#12151A"
  surface-raised: "#1A1E25"
  border: "#23272E"
  text-primary: "#E7E9EC"
  text-muted: "#9AA1AC"
  signal-blue: "#4C8DFF"
  verdict-entailed: "#5FBE87"
  verdict-contradicted: "#E5675F"
  verdict-not-enough-info: "#D4A657"
typography:
  display:
    fontFamily: "Space Grotesk, ui-sans-serif, system-ui"
    fontWeight: 600
  body:
    fontFamily: "Space Grotesk, ui-sans-serif, system-ui"
    fontWeight: 400
  mono:
    fontFamily: "Space Mono, ui-monospace, SFMono-Regular, monospace"
    fontWeight: 400
rounded:
  sm: "6px"
  md: "8px"
  pill: "999px"
spacing:
  xs: "4px"
  sm: "8px"
  md: "16px"
  lg: "24px"
  xl: "40px"
---

# Design System: Hallucination / Factual-Consistency Scorer — Report Viewer

## Overview

**Creative North Star: "The Evidence Docket"**

This is not a marketing surface — it's a dashboard for a technical reviewer who wants to see the work, not
take a claimed score on faith. The visual model is the tooling this audience already lives in daily: CI
dashboards, eval harnesses, terminal log output. Dark ground, monospace numbers, no gradients or gloss. The
product's real differentiator is that every aggregate number decomposes into visible claims with judge
reasoning attached — the design's job is to make that decomposition feel like the natural, expected state of
the page, not a hidden drawer.

Confirmed rejection: no trust-badge/pass-fail iconography that oversells a number beyond what the docs
support (per `PRODUCT.md`'s "real numbers, honestly caveated" principle). No light-mode "friendly SaaS
dashboard" register — this reads as a technical instrument, not a product marketing page.

**Key Characteristics:**
- Dark, near-black tonal surfaces — depth via lightness steps, not shadows
- Space Mono for every number, score, and reasoning string — signals "this is a real transcript"
- One restrained accent (signal blue) reserved for actions/emphasis, never used for verdicts
- Verdict state carried entirely by three fixed semantic colors, consistent everywhere they appear

## Colors

Restrained strategy: neutrals carry the surface; one accent is spent sparingly; verdict states are their
own fixed semantic vocabulary, never reused for anything else.

### Primary
- **Signal Blue** (`#4C8DFF`): the one accent. Primary actions, links, active/focus states, section
  headers' rule line. Used on roughly 5–10% of any given viewport — its rarity is what makes it read as
  "this matters," never as decoration.

### Neutral
- **Ink** (`#0A0C0F`): page background.
- **Surface** (`#12151A`): section panels, table rows at rest.
- **Surface Raised** (`#1A1E25`): expanded row / hovered row / stat cards — the "lifted" tonal step.
- **Border** (`#23272E`): hairline dividers, table borders, card outlines. Always 1px, never a shadow.
- **Text Primary** (`#E7E9EC`): headings, primary values.
- **Text Muted** (`#9AA1AC`): labels, captions, secondary metadata (timestamps, counts).

### Named Rules
**The Verdict Isolation Rule.** `verdict-entailed`, `verdict-contradicted`, and `verdict-not-enough-info`
are reserved exclusively for the three judge verdicts. They never appear as decoration, chart color, or
generic status elsewhere in the UI — if a color could be mistaken for a verdict, it isn't one of these
three.

- **Entailed** (`#5FBE87`): desaturated green, verdict tag + expanded-claim left border only.
- **Contradicted** (`#E5675F`): desaturated red, same usage pattern.
- **Not Enough Info** (`#D4A657`): desaturated amber, same usage pattern.

## Typography

**Display Font:** Space Grotesk (with ui-sans-serif, system-ui fallback)
**Body Font:** Space Grotesk (with ui-sans-serif, system-ui fallback)
**Label/Mono Font:** Space Mono (with ui-monospace, SFMono-Regular, monospace fallback)

**Character:** Space Grotesk carries structure — headings, nav, labels, prose — with a slightly technical,
geometric edge that avoids generic system-UI neutrality. Space Mono is reserved for anything that is data:
scores, percentages, counts, timestamps, claim text, and judge-written reasoning strings, so the reader's
eye learns instantly which is a UI label and which is real transcript content.

### Hierarchy
- **Display** (600, clamp(1.75rem, 3vw, 2.5rem), 1.1): page title / headline stat value.
- **Headline** (600, 1.25rem, 1.2): section titles ("Benchmark Results", "Live Scoring History").
- **Title** (500, 1rem, 1.3): stat card labels, table column headers (uppercase, letter-spacing 0.04em).
- **Body** (400, 0.9375rem, 1.5): prose, empty-state copy, descriptions. Max ~70ch.
- **Label** (500, 0.75rem, 1.3, uppercase, letter-spacing 0.06em): verdict tags, badges, metadata chips.
- **Mono/Data** (400, 0.875rem, 1.6, Space Mono): scores, claim text, reasoning, timestamps, all table
  numeric cells.

### Named Rules
**The One Typeface Signals Data Rule.** If it's a number, a score, a percentage, a claim's exact text, or a
judge's reasoning string, it renders in Space Mono. Everything else — labels, nav, prose — is Space
Grotesk. No third typeface.

## Layout

Single-page, centered container, max-width 1280px, horizontal padding 24px (mobile) → 40px (desktop).
Vertical rhythm: sections separated by 40px, internal card/row padding 16–24px. Grid model: a 4-column stat
strip (collapsing to 2 columns on mobile) immediately below the page header, then two full-width stacked
sections (Benchmark Results, Live Scoring History), each its own bordered panel. Tables are full-width
within their panel; expanding a row inserts an inline detail block rather than navigating away or opening a
modal, keeping scroll position and surrounding rows visible.

Responsive: stat strip and table columns collapse gracefully at ~640px; on narrow viewports, table rows
reflow to a stacked card layout per example rather than horizontal-scrolling a wide table.

## Elevation & Depth

Flat by default — no drop shadows anywhere. Depth is conveyed entirely through the Ink → Surface → Surface
Raised tonal ramp: a raised element is simply a lighter flat surface, not a surface with a shadow under it.
The one exception is a subtle 1px inset border (`border` color) that appears on the expanded state of a
table row, marking its boundary without adding weight.

### Named Rules
**The Flat Instrument Rule.** This is read as an instrument panel, not a stack of paper. Nothing lifts off
the page via shadow; state changes read through background-lightness and border only.

## Shapes

Small, consistent radius (6px) on cards, panels, and buttons — enough to soften the terminal starkness
without becoming a "friendly app" register. Verdict tags and metadata chips are fully pill-shaped (999px
radius) as the one deliberately different silhouette in the system, making them instantly recognizable as
status, not content. Borders are always 1px hairlines in the `border` neutral; no double borders, no
heavy strokes.

## Components

### Stat Card
- **Shape:** 6px radius, 1px `border` outline, `surface-raised` background.
- **Content:** Title-weight label (muted) above a Display/Mono-weight value.
- **Distinctive behavior:** the F1/naive-baseline pair renders as two stacked mono values with a thin
  connecting rule between them, making the margin visually explicit rather than requiring the reader to
  do the subtraction themselves.

### Verdict Tag
- **Shape:** pill (999px), Label typography, uppercase.
- **Color:** background is the verdict color at ~16% opacity over `surface`, text and 1px border are the
  full-opacity verdict color. Never filled solid — keeps the dark surface legible and avoids the tag
  reading as a "success/error toast."

### Table / Expandable Row
- **Rest state:** `surface` background, 1px bottom `border`, Mono typography for numeric/data cells.
- **Hover:** background steps to `surface-raised`.
- **Expanded state:** row background becomes `surface-raised`, reveals an inline block below it per claim —
  each claim line shows the claim text (Mono), its Verdict Tag, and the judge's reasoning string (Mono,
  `text-muted`) with a 2px left border in that claim's verdict color.

### Section Panel
- **Shape:** 6px radius, 1px `border`, `surface` background, 24px internal padding.
- **Header:** Headline typography, left-aligned, with a 2px `signal-blue` rule sitting under the section
  title only (not the whole panel) — the one recurring appearance of the accent color as a wayfinding
  device.

### Empty / Loading / Error States
- **Empty:** centered Body text in `text-muted`, no illustration — a plain, honest sentence (e.g. "No live
  scoring calls yet — run `POST /v1/score` to populate this section.").
- **Loading:** skeleton blocks in `surface-raised` at the shape of the real content, no spinner.
- **Error:** plain bordered panel (standard 1px `border`, no verdict color — errors aren't a verdict, so
  the Verdict Isolation Rule keeps them out of that palette), a small "Error" label, factual copy only, no
  alarmist iconography.

## Do's and Don'ts

### Do:
- **Do** render every score, percentage, count, timestamp, claim, and reasoning string in Space Mono.
- **Do** keep `signal-blue` to actions, links, focus states, and the section-title rule — never verdicts.
- **Do** state empty/error states as plain honest sentences, matching `PRODUCT.md`'s "never hide an
  unfavorable qualifier" principle.
- **Do** use pill shapes exclusively for verdict tags and metadata chips, never for buttons or cards.

### Don't:
- **Don't** use `verdict-entailed` / `verdict-contradicted` / `verdict-not-enough-info` for anything other
  than the three judge verdicts.
- **Don't** add drop shadows anywhere — depth is tonal only.
- **Don't** add a light-mode theme, gamified badges, or trust-score iconography beyond what the real
  numbers support.
- **Don't** open a modal or navigate away for claim-level detail — rows expand inline.
