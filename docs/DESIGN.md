# Cost Review — Visual Baseline

Status: approved visual direction, aligned with Product Specification v1.0.

The visual tokens and interaction principles in this document remain approved.
Where the earlier expense-only information architecture conflicts with Product
Specification v1.0, the Product Specification takes precedence.

## 1. Direction: Nordic Financial Calm

Cost Review should feel like a calm modern analysis tool, not an accounting package and not a brightly gamified fintech app. The visual language combines Scandinavian restraint, generous whitespace, soft surface contrast, and precise financial typography.

The interface is light-mode first. Design tokens must make a future dark theme possible without redesigning components.

## 2. Color system

| Role | Token | Value | Use |
|---|---|---:|---|
| Canvas | background | #F5F6F4 | Application background |
| Surface | surface | #FFFFFF | Panels, tables, dialogs |
| Primary text | text-primary | #202522 | Headings, values, body text |
| Secondary text | text-secondary | #747B77 | Metadata and helper text |
| Border | border | #DFE5E1 | Subtle separators and controls |
| Primary accent | accent | #477568 | Primary actions, selection, focus context |
| Accent hover | accent-strong | #365F54 | Hover and pressed primary action |
| Analysis blue | analysis-blue | #587A92 | Secondary comparison series |
| Sand | analysis-sand | #C49A67 | Third comparison series |
| Warning | warning | #C5823B | Items needing attention |
| Destructive | destructive | #B95D59 | Delete actions and destructive errors |

A large amount is data, not an error. Never use red merely because a cost is high. Reserve warning and destructive colors for semantic states.

Default charts should not assign a saturated color to every category. Use the primary accent, quiet tonal variations, or neutrals; introduce blue and sand when comparison gives color a clear semantic role.

## 3. Typography

Use Inter when available, with the system sans-serif stack as fallback. Text should feel crisp and understated.

- Primary financial value: 36–44 px desktop, 34 px mobile, weight 650–700.
- Page title: 24–30 px, weight 650.
- Section title: 14–16 px, weight 650.
- Body: 14–16 px.
- Metadata and labels: 11–13 px.
- Use tabular numerals for amounts, dates, percentages, and aligned comparisons.
- Avoid all caps except for very short eyebrow labels with generous letter spacing.

## 4. Layout and surfaces

Use a centered content canvas with a comfortable desktop maximum width around 1180–1240 px. Maintain generous outer padding and a consistent 8 px spacing rhythm.

Surfaces use 10–14 px corner radii, a subtle #DFE5E1 border, and little or no shadow. Prefer hierarchy through spacing, type, and tonal surfaces over floating-card effects.

Do not build a dashboard full of small KPI cards. Give the single most important value—normalized recurring cost—space in a hero area, then use a limited number of larger analytical panels.

Tables use weak horizontal dividers, comfortable row height, aligned numeric columns, and sticky headers only when they materially help scanning.

## 5. Navigation

The Release 1 information architecture expands beyond the original
expense-only prototype. Primary destinations are expected to include:

- Overview
- Transactions
- Expenses
- Income
- Analysis
- Budget
- Investments
- Attention
- Settings

Desktop navigation sits in a calm top bar with the Cost Review wordmark. The current destination is indicated by weight, text color, and a soft accent treatment—not a loud block. On narrow screens navigation may scroll horizontally or collapse into an accessible menu.

Production and Demo/Test context is always visible in the application chrome.
Demo/Test uses both a persistent text label and a distinct quiet surface
treatment; environment identity must never rely on color alone.

Sprint 1 may expose only the destinations that are implemented. Placeholder
navigation must not imply that financial workflows already work.

## 6. Overview composition

For the recurring-cost portion of a future Overview, the approved information
hierarchy is:

1. Eyebrow: Recurring cost.
2. Dominant value such as 14 620 kr / month.
3. Annual equivalent and active Expense count.
4. Monthly, Quarterly, Annual segmented control.
5. Cost by category and Largest commitments side by side on wide screens.
6. Upcoming actual payments across the content width.
7. A quiet review-attention strip with one clear action.

The first Sprint may show an honest empty state or structural preview, but must not imply that sample financial figures are live user data.

## 7. Analysis interactions

Analysis may be denser than Overview because the user has explicitly entered an exploration workspace. Interactions are part of the visual language:

- Hover reveals exact underlying values.
- Selecting a category or Provider highlights it across related visuals.
- Clicking a chart element filters or drills down to the contributing Expenses.
- Selected comparison entities appear as removable chips.
- Clear actions visibly restore the full dataset.
- Normalization period and analysis range remain distinct controls.

Charts should remain legible without relying only on color. Provide labels, values, tooltips, focus states, and an accessible tabular alternative for important data.

## 8. Components and states

Buttons have one clear primary treatment, quiet secondary and ghost treatments, and a separate destructive treatment. Tags and filter chips use soft backgrounds and can represent category, recurrence, status, or Provider consistently.

Forms place visible labels above controls, explanatory text below only when necessary, and validation adjacent to the affected field. Searchable Provider and Category selectors support keyboard navigation and an inline create option.

Every data region defines loading, empty, error, and populated states. Empty states should explain what will appear and offer the most relevant next action. Avoid fake skeleton content that can be mistaken for real financial data.

Destructive operations require explicit confirmation and clearly describe affected records. Success and error feedback must not rely on color alone.

## 9. Motion and accessibility

Use short, restrained transitions, generally 120–180 ms. Respect prefers-reduced-motion. Motion may clarify selection and hierarchy but must never block work.

All controls need visible keyboard focus, meaningful accessible names, logical tab order, and at least WCAG AA contrast. Touch targets should be approximately 44 px. Content must reflow without horizontal page scrolling at 320 px, except intentionally scrollable tables or navigation.

## 10. Responsive behavior

At tablet widths, analytical grids collapse to one column while preserving hierarchy. At mobile widths, reduce outer padding before reducing content legibility; keep the primary amount prominent; allow segmented controls and navigation to scroll when needed; hide only secondary metadata, never required context or actions.

## 11. Content style

Use direct, neutral language. Prefer Recurring cost, Monthly equivalent, Actual payment, Estimated, Active, and Needs review. Avoid judgmental labels such as bad spending or expensive problem. Use Swedish locale formatting for the initial product: spaces as thousands separators, comma decimals, SEK shown as kr, and ISO-safe storage behind the presentation layer.
