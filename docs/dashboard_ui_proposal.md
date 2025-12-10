# Dashboard UI Concept (Content Generation Focus)

## Objectives
- Present a modern, minimal interface optimized for creating and organizing marketing campaign content across blogs, LinkedIn, and social channels.
- Emphasize planning, collaboration, and content quality—no controls for launching or running ads.
- Make it easy to sort, filter, and group by campaign category/topic to keep the library navigable as it grows.
- Highlight production outputs (volume, coverage by category/topic, model usage) instead of downstream performance metrics.

## Layout & Information Architecture
- **Top bar**: Brand logo/title; global search (campaign, asset, keyword); quick actions (New Campaign, Import Brief); notifications and user menu.
- **Left navigation** (collapsible): Dashboard, Campaigns, Content Library, Calendar, Insights, Audience, Automations, Settings.
- **Dashboard canvas** (modular cards):
  - **Campaign overview cards**: For active/planned campaigns, show content pipeline status (Ideas → Draft → Scheduled → Published), owners, and category/topic chips. Replace CTR/conversion metrics with creation velocity (pieces/week), on-time rate, and approval status.
  - **Creation activity timeline**: Line/area chart of content published/scheduled per day or week, filterable by channel and category/topic. Optional overlay for average draft-to-publish duration.
  - **Content pipeline snapshot**: Kanban-style lanes with platform badges (LinkedIn, Blog, X, IG) and avatars. Inline actions for move, assign, comment, and request approval.
  - **Upcoming schedule**: Two-week strip/calendar with drag-and-drop rescheduling; surfaces platform icons, categories, and content status.
  - **Tasks & approvals**: Lightweight list for reviews with due dates and assignees; quick approve/reject.
  - **Insights & recommendations**: Alerts for gaps ("No content scheduled next week for Product Launch"), coverage (“AI model A used 70% for thought leadership”), and AI suggestions (“Repurpose top-performing blog into LinkedIn carousel”).
  - **Category/topic coverage**: Matrix or stacked bars showing content count by category/topic and channel; highlight under-served categories.

## Category/Topic Management
- **Sorting & grouping**: Persistent controls to sort campaigns and content by category/topic; include alphabetical, priority, recency, and production-volume options.
- **Filters**: Multi-select category/topic chips, channel filters (LinkedIn/Blog/Social), tags, owners, model used, and date range. Filters remain sticky as users scroll.
- **Empty/overloaded states**: If no category is assigned, prompt users with a friendly chip selector; for crowded views, allow quick collapsing by category.

## Visual Style
- Neutral background with charcoal text; single accent color (teal or indigo) for primary actions and highlights.
- Inter or similar sans-serif; clear hierarchy (H1 page title, H3 section headers, 14–16px body, 13px meta labels).
- Cards with 8–12px radius, subtle elevation, consistent 8px spacing grid. Use compact badges for status, platforms, categories, and model source.
- Accessible focus states and contrast; outline-style icon set for consistency.

## Interaction & UX Patterns
- **Inline edits**: Quick status changes (mark ready for review, reschedule), drag-and-drop scheduling, inline category/topic edits via chips.
- **Feedback**: Toasts for saves/updates; optimistic UI for minor actions; skeleton/loading states for charts and lists.
- **Collaboration**: Comment threads with @mentions, approval checkpoints, and file attachments for briefs/assets.
- **Guidance**: Contextual tooltips for production metrics (velocity, coverage), dismissible hints, and a short onboarding checklist to connect channels/import content.

## Content Production Views (No Campaign Performance Reporting)
- **Production KPIs**: Publish velocity (per week), approval rate, average draft-to-publish time, originality score, and model usage mix—each with small sparkline trends and WoW deltas.
- **Coverage insights**: Stacked bars or grid showing how many pieces exist per category/topic and channel; call out empty/low-volume areas.
- **Content quality table**: Sortable by publish date, category/topic, originality score, review status, and model used. Platform chips and quick actions to "Repurpose" or "Request edits." No spend/CTR/conversion fields.

## Responsive & Dark Mode
- Responsive grid that collapses to single-column on mobile; sticky filters adapt to a bottom sheet.
- Dark mode with muted accents, desaturated chart backgrounds, and brighter data lines.

## Practical Implementation Notes
- Debounce filter queries; lazy-load heavy charts; cache category/topic lists for snappy sort/filter interactions.
- Use consistent tokens for spacing, typography, colors, and elevation.
- Maintain ARIA labels and keyboard navigation for all interactive controls (filters, cards, Kanban, calendar).

## Wireframe Outline

### Hero View (Desktop)
- **Top bar (full width, fixed)**: Logo/title on the far left; centered global search; right-aligned quick actions (New Campaign, Import Brief), notification bell, and user avatar.
- **Left navigation (fixed rail)**: Vertical icons + labels for Dashboard, Campaigns, Content Library, Calendar, Insights, Audience, Automations, Settings. Collapse affordance pinned at the bottom.
- **Primary filter row (below top bar, spans canvas)**: Category/topic chip group with multi-select; channel toggles; owner dropdown; model-used dropdown; date range selector; “Save segment” pill on the right.
- **Main grid (two columns)**:
  - **Left column (70%)**
    - **Campaign overview band (horizontal cards)**: 3–4 cards per row showing campaign name, category/topic chips, owners, readiness bar (Ideas→Draft→Scheduled→Published), creation velocity, and approval rate.
    - **Creation activity timeline (full-width card)**: Line/area chart of drafts/scheduled/published counts with tabs for All/LinkedIn/Blog/Social; comparison toggle (WoW/30d/90d); legend below chart.
    - **Content pipeline snapshot (Kanban strip)**: Four lanes (Ideas, Draft, Scheduled, Published) with draggable tiles. Tiles show platform badge, title, category chip, assignee avatar, and model used.
    - **Insights & recommendations (2-up cards)**: Alert-style cards flagging coverage gaps, upcoming content droughts, and AI repurposing prompts.
  - **Right column (30%)**
    - **Upcoming schedule (calendar strip)**: Two-week horizontal strip with day columns; each entry shows platform icon, title, status, category chip, and model used. Drag-and-drop enabled.
    - **Tasks & approvals (stacked list)**: Rows with task name, due date, assignee avatar, status badge, and quick approve/reject buttons.
    - **Production KPI tiles (2x2 grid)**: Publish velocity, approval rate, draft-to-publish time, originality score—each with tiny sparkline and WoW delta.
    - **Category/topic coverage (mini matrix)**: Compact heatmap showing counts by category vs. channel, with tooltips for details.

### Tablet Adjustments (md breakpoint)
- Collapse left navigation into icon-only rail; top bar condenses search into an icon that expands on tap.
- Primary filter row becomes a horizontally scrollable chip bar; “Save segment” moves into an overflow menu.
- Main grid shifts to a single-column stack; Kanban and calendar remain horizontally scrollable.

### Mobile Layout (sm breakpoint)
- **Top bar**: Logo + search icon; kebab menu opens navigation drawer and quick actions.
- **Filters**: Sticky bottom sheet with category/topic chips, channel toggles, and model-used selector; slide-up panel for advanced filters.
- **Content**: Single-column cards; creation activity chart switches to minimal sparkline with toggle chips above; Kanban shows one lane at a time with a lane switcher.
- **Tasks/schedule**: Condensed list with swipe actions (complete/approve/reschedule).

### Key States & Interactions
- **Empty state**: Hero card prompting “Create your first campaign”; sample data toggle; illustration placeholder.
- **Loading state**: Skeleton cards for campaign band, chart shimmer, and skeleton rows for tasks/schedule.
- **Error/alert state**: Inline banners within cards; retry buttons positioned top-right of the affected card.
- **Editing**: Inline chip editor for category/topic on cards and tiles; drag-and-drop reorder with drop targets highlighted.
- **Dark mode**: Invert surfaces with muted accent; chart gridlines fade, data lines brighten; focus rings remain high-contrast.
