# Bounty User Manual

Bounty is the DockLabs suite's federal-funds discovery platform. It pulls
federal grant opportunities from Grants.gov, scores them against your
agency's priorities with AI, and gives a coordinator the tools to track
each opportunity through preparation, internal approval, application, and
award.

This manual covers the user-facing surface end to end. For operations and
deployment notes, see [CLAUDE.md](../CLAUDE.md).

---

## Contents

1. [Overview](#overview)
2. [Roles](#roles)
3. [Getting Started](#getting-started)
4. [Federal Opportunities (Public Portal)](#federal-opportunities-public-portal)
5. [Tracked Opportunities](#tracked-opportunities)
6. [AI Matching](#ai-matching)
7. [Match Preferences](#match-preferences)
8. [State Preferences](#state-preferences)
9. [Collaboration](#collaboration)
10. [Internal Approval & Manifest Signing](#internal-approval--manifest-signing)
11. [Harbor Handoff (Award)](#harbor-handoff-award)
12. [Helm Inbox Integration](#helm-inbox-integration)
13. [Notifications](#notifications)
14. [Status Reference](#status-reference)
15. [Programmatic API](#programmatic-api)
16. [Keyboard Shortcuts](#keyboard-shortcuts)
17. [Support](#support)

---

## Overview

Bounty has two surfaces:

- **The public portal** — `/` and `/opportunities/` — a browsable catalog
  of federal grant opportunities synced from Grants.gov. No login
  required. Use it to search, filter, and read opportunity detail.
- **The coordinator workspace** — `/dashboard/`, `/tracked/`, `/matching/`,
  `/integration/` — the authenticated surface where coordinators claim
  opportunities, run AI matching, invite collaborators, attach diligence
  documents, and push awarded grants into Harbor.

Bounty does not store the program-management state of an awarded grant —
that lives in **Harbor** once the opportunity is pushed downstream.

---

## Roles

Bounty roles are issued via Keel SSO and surfaced in your sidebar profile.

| Role | Capability |
|---|---|
| **Admin** (`admin`) | Full access. Manage state preferences, all tracked opportunities, Harbor connection, and demo data. |
| **Coordinator** (`coordinator`) | Drive opportunities through their lifecycle. Claim, invite collaborators, transition status, attach files, send for signing, push to Harbor, manage state preferences. |
| **Analyst** (`analyst`) | Track opportunities, run AI matching, comment, and attach files on opportunities they're invited to. Cannot manage state preferences or push to Harbor. |
| **Viewer** (`viewer`) | Read-only across the dashboard and opportunities they're invited to. |

Suite-level `system_admin` inherits Admin behavior on Bounty.

---

## Getting Started

### Signing in

1. Visit `https://bounty.docklabs.ai/` (or your tenant's host).
2. Click **Sign in with DockLabs** (the suite OIDC button).
3. You'll land on `/dashboard/`.

If you're already signed in to another DockLabs product, the redirect is
seamless — no second login form.

### What you'll see first

- **Dashboard** — summary tiles for your tracked opportunities, new
  high-relevance matches, and pending actions.
- **Sidebar** — Federal Opportunities (public portal), Tracked, AI
  Matching (if you have AI access), and Harbor Connection (coordinators).

---

## Federal Opportunities (Public Portal)

`/` and `/opportunities/` — the public-facing catalog of every federal
opportunity Bounty has cached from Grants.gov. Anyone can read it; no
login required.

Each opportunity carries:

- **Title**, **opportunity number** (NOFO), and **opportunity ID**.
- **Agency** name and code.
- **Category** and **funding instrument** (grant, cooperative agreement,
  procurement contract, other).
- **CFDA numbers** (Catalog of Federal Domestic Assistance).
- **Award range** — floor, ceiling, expected number of awards, total
  funding pool.
- **Post date**, **close date**, and **archive date**.
- **Eligibility** — applicant types and free-text eligibility narrative.
- **Status** — Posted, Closed, Archived, or Forecasted.
- **Grants.gov URL** — deep link to the source listing.

### Search & filter

- **Free-text search** — title and description.
- **Filter** — by agency, status, and category.
- **Instant typeahead** — `GET /opportunities/instant/?q=…` returns the
  top hits as you type.
- **AI chat search** — `GET /opportunities/chat/?q=…` returns a
  Claude-powered narrative match against your query.

The public portal extends `base_public.html`. The authenticated workspace
extends `base.html`.

---

## Tracked Opportunities

`/tracked/` — the coordinator pipeline. Each row represents a federal
opportunity your team is actively working.

Each tracked opportunity carries:

- **Federal opportunity** — the source record from the public catalog.
- **Tracked by** — the current principal driver (set via Claim).
- **Status** — Watching, Preparing, Approved, Applied, Awarded, Declined.
- **Priority** — Low, Medium, High.
- **Notes** — free-text working notes.
- **Collaborators** — people invited with explicit roles.
- **Attachments** — typed diligence files (briefings, drafts, signed PDFs,
  evidence).
- **Status history** — every transition logged with actor + comment.
- **Harbor push status** — whether this opportunity has been pushed to
  Harbor as a `GrantProgram`.

### Lifecycle

Bounty follows the **DockLabs Project Lifecycle Standard**:

> claim → invite collaborators → diligence (notes + attachments) →
> stage progression → optional handoff to Manifest for signing →
> signed-doc roundtrip → optional downstream export to Harbor

Status transitions:

```
watching → preparing → approved → applied → awarded
                                 \         \→ declined
                                  → applied (no approval)
preparing → watching (back)
approved → preparing (back)
watching → declined (direct decline)
```

`approved` is the gated state where Manifest signing fires. Use it when
your agency requires an internal sign-off on the application package
before it goes to Grants.gov.

### Tracking a new opportunity

1. From a public opportunity detail page, click **Track this opportunity**.
2. Bounty creates a `TrackedOpportunity` row with you as the principal
   driver (`tracked_by=you`, `status=Watching`, `priority=Medium`) and
   opens an `OpportunityAssignment` row recording the claim.
3. The opportunity is now visible at `/tracked/`.

### Claim & release

A tracked opportunity has exactly one **principal driver** (`tracked_by`).
Open assignments are tracked in an `OpportunityAssignment` history.

- **Claim** — `/tracked/<id>/claim/` — make yourself the driver. Closes
  any prior open assignment, opens a new one with
  `assignment_type=CLAIMED` (or `MANAGER_ASSIGNED` if a manager assigns
  on someone else's behalf).
- **Release** — `/tracked/<id>/release/` — return the opportunity to the
  unowned pool. Closes the active assignment with `status=RELEASED`.

---

## AI Matching

`/matching/recommendations/` — AI-scored matches between your preferences
and every open federal opportunity. Available to users with an Anthropic
API key configured (either personal — set on your profile — or the
suite-wide `ANTHROPIC_API_KEY`).

Each match carries:

- **Relevance score** — 0–100, produced by Claude scoring your
  preferences against the opportunity title, description, and metadata.
- **Explanation** — short narrative explaining why this opportunity is or
  isn't a fit.
- **Status** — New, Viewed, Saved, Dismissed.
- **Feedback** — optional thumbs up / down with a reason
  (wrong focus, budget too large/small, already aware, not eligible,
  not relevant, other). Feedback feeds back into future scoring.

### Match score thresholds

Bounty configures three thresholds:

| Setting | Default | Meaning |
|---|---|---|
| `GRANT_MATCH_MIN_SCORE` | 60 | Minimum score stored as a match. Below this, the opportunity isn't surfaced. |
| `GRANT_MATCH_NOTIFY_SCORE` | 75 | Score at which a `grant_match_found` notification fires. |
| `GRANT_MATCH_HIGH_SCORE` | 90 | Score at which a `grant_match_high_score` notification fires (priority high). Also the threshold for the Helm "Awaiting Me" inbox. |

### Running matching

- **Run matching** — `/matching/recommendations/run/` — POST scans all
  open federal opportunities against your preferences and stores
  `OpportunityMatch` rows for any score ≥ `GRANT_MATCH_MIN_SCORE`.
- **Mark viewed** — `/matching/recommendations/mark-viewed/` — POST
  flips your NEW matches to VIEWED so they stop showing up as new.
- **Dismiss** — `/matching/dismiss/<id>/` — POST sets a single match's
  status to DISMISSED.
- **Track and dismiss** — `/matching/track-dismiss/<id>/` — POST tracks
  the underlying opportunity (creates a `TrackedOpportunity`) and
  dismisses the match in one click.
- **Feedback** — `/matching/feedback/<id>/` — POST records a thumbs
  up/down with an optional reason.

---

## Match Preferences

`/matching/preferences/` — your personal preferences for AI matching.

Fields:

- **Focus areas** — multi-select from a fixed taxonomy: Education;
  Health & Human Services; Environment & Energy; Infrastructure &
  Transportation; Public Safety; Housing & Community Development;
  Economic Development; Arts & Culture; Technology & Innovation;
  Agriculture & Food; Workforce Development; Justice & Legal Services;
  Other.
- **Keywords** — free-text terms describing your priorities.
- **Funding range** — minimum and maximum dollar amounts you're
  realistically eligible for.
- **Description** — narrative paragraph the AI uses for context.
- **Digest frequency** — None, Daily, or Weekly. Controls the cadence of
  match-summary emails.

When matching runs, Bounty merges your personal preferences with the
active state preference (see below) so individual users inherit the
state-wide baseline without retyping it.

---

## State Preferences

`/matching/state-preferences/` — coordinator-only. The state-wide
matching baseline that every user inherits.

Fields mirror Match Preferences (focus areas, keywords, funding range,
description). Only one `StatePreference` is active at a time.

Use case: a state economic-development office sets a baseline
("infrastructure, broadband, workforce; $1M–$50M; we are CT DECD
focused on…") and individual coordinators layer their own focus on top.
Matching scores against the union.

---

## Collaboration

### Per-opportunity roles

| Role | What they can do |
|---|---|
| **LEAD** | Drive the opportunity. Transition status, manage collaborators, send for signing, push to Harbor, mark awarded/declined. |
| **CONTRIBUTOR** | Update notes, attach files, comment. |
| **REVIEWER** | Read everything; comment on notes and attachments. |
| **OBSERVER** | Read-only access. |

Only LEAD / CONTRIBUTOR / REVIEWER / OBSERVER are valid (suite-wide
convention).

### Inviting collaborators

1. Open a tracked opportunity → **Add collaborator**.
2. Pick a user (or enter an email for an external invitee) and a role.
3. The invitee gets an in-app notification.

`/tracked/<id>/collaborate/` — add. `/tracked/<id>/collaborate/<collab_id>/remove/`
— remove.

### Attachments

`/tracked/<id>/attachments/` — drag-and-drop file uploads. Each
attachment carries a **source** (manual upload, manifest_signed, etc.)
and a **visibility** flag (internal vs external). Files attached as
`manifest_signed` are produced automatically by the Manifest signing
roundtrip — you never upload them by hand.

`/tracked/<id>/attachments/<attachment_id>/delete/` — remove.

---

## Internal Approval & Manifest Signing

When an agency requires an internal sign-off on the application package
before submission, Bounty hands the package to **Manifest** for an
ordered-signer workflow.

### Send for signing

`/tracked/<id>/sign/send/` — LEAD only. Available when:

1. The opportunity is in `preparing` status.
2. Manifest is configured (`MANIFEST_URL` and `MANIFEST_API_TOKEN` are
   set).

Bounty calls `keel.signatures.client.send_to_manifest` with:

- Source object — the `TrackedOpportunity`.
- Signers — chosen via the Send for Signing form.
- On approval — transition to `approved`.

When Manifest finishes the packet, the inbound webhook fires the
`packet_approved` signal. Bounty's signal receiver:

1. Files the signed PDF as an `OpportunityAttachment` with
   `source=manifest_signed` and the Manifest packet UUID.
2. Transitions the opportunity to `approved`.
3. Notifies the LEAD and active collaborators.
4. Registers the attachment for FOIA export.

### Local-sign fallback

`/tracked/<id>/sign/local/` — when Manifest isn't configured (standalone
deployment), the LEAD can upload a manually-signed PDF instead. The
attachment is filed with `source=local_signed` and the opportunity
transitions to `approved` on submission.

The Send for Signing button is **hidden** when Manifest isn't available
— there are no silent no-ops.

---

## Harbor Handoff (Award)

When an opportunity is **awarded**, the LEAD can push it into Harbor as a
`GrantProgram` so program staff can manage applications, awards, and
compliance there.

### Configure Harbor

`/integration/harbor/settings/` — coordinator-only. Provide:

- **Harbor URL** — base URL of the Harbor deployment.
- **API token** — outbound auth.

### Push to Harbor

`/integration/harbor/push/<id>/` — LEAD-only. Available when:

1. The opportunity is in `awarded` status.
2. Harbor settings are configured.

The push is best-effort. On success, `tracked.harbor_program_id` is set
to Harbor's program ID and `harbor_push_status` flips to `pushed`. On
failure, status flips to `failed` with a retry control surfaced. Either
way, the underlying tracked opportunity is unaffected.

The button is hidden when Harbor isn't configured.

---

## Helm Inbox Integration

Helm's per-user **Awaiting Me** column queries Bounty's
`/api/v1/helm-feed/inbox/` endpoint and surfaces, for each user:

- **NEW high-relevance matches** — `OpportunityMatch` rows with
  `status=NEW` and `relevance_score >= GRANT_MATCH_HIGH_SCORE` (default
  90), capped at 50 items, ordered by score descending.
- **Unread notifications** — every unread `Notification` for the user.

Each item carries a deep link back into Bounty (typically
`/matching/recommendations/`) so the user can act with one click.

The aggregate feed at `/api/v1/helm-feed/` powers Helm's "Across the
suite" dashboard cards.

---

## Notifications

Bounty notification events:

| Event | When it fires |
|---|---|
| `grant_match_found` | A new opportunity match scored ≥ `GRANT_MATCH_NOTIFY_SCORE` (75). |
| `grant_match_high_score` | A new opportunity match scored ≥ `GRANT_MATCH_HIGH_SCORE` (90). Priority high. |
| `opportunity_collaborator_invited` | You were added as a collaborator on a tracked opportunity. |
| `opportunity_status_changed` | A tracked opportunity you're on transitioned. |
| `opportunity_signed` | A Manifest signing roundtrip completed for your tracked opportunity. |
| `harbor_push_succeeded` | An awarded opportunity was pushed to Harbor successfully. |
| `harbor_push_failed` | A push to Harbor failed; retry available. |

Channels (in-app + email) are user-configurable at
`/notifications/preferences/`. The link is in the sidebar user-menu
dropdown.

---

## Status Reference

### Tracked opportunity status

| Status | Meaning |
|---|---|
| **Watching** | On your radar; no active preparation yet. |
| **Preparing** | Application package being prepared. |
| **Approved** | Internally approved (typically via Manifest signing). |
| **Applied** | Submitted to Grants.gov. |
| **Awarded** | Award received. Harbor handoff available. |
| **Declined** | Not awarded, or chose not to apply. |

### Federal opportunity status

| Status | Meaning |
|---|---|
| **Posted** | Open and accepting applications. |
| **Closed** | Past close date. |
| **Archived** | Removed from Grants.gov. |
| **Forecasted** | Anticipated; not yet posted. |

### Collaborator role

| Role | Read | Comment | Edit | Manage |
|---|---|---|---|---|
| **LEAD** | yes | yes | yes | yes |
| **CONTRIBUTOR** | yes | yes | yes | — |
| **REVIEWER** | yes | yes | — | — |
| **OBSERVER** | yes | — | — | — |

### Match status

| Status | Meaning |
|---|---|
| **New** | Just produced; awaiting your review. |
| **Viewed** | You've seen it but not acted. |
| **Saved** | Marked for follow-up. |
| **Dismissed** | Not relevant; filtered out of the recommendations list. |

---

## Programmatic API

`/api/v1/` — DRF resource endpoints. Auth: per-user Bearer token (SHA-256
hashed; set on `BountyProfile`).

| Resource | Endpoint |
|---|---|
| Federal opportunities (read) | `/api/v1/opportunities/` |
| Tracked opportunities | `/api/v1/tracked/` |
| Match preferences | `/api/v1/preferences/` |
| Opportunity matches | `/api/v1/matches/` |
| Helm feed (aggregate) | `/api/v1/helm-feed/` |
| Helm feed (per-user inbox) | `/api/v1/helm-feed/inbox/?user_sub=…` |

Pagination envelope: `{total, limit, offset, results}`. Default 50, max
200.

OpenAPI schema is auto-generated; browse it at `/api/schema/`,
`/api/docs/` (Swagger UI), or `/api/redoc/`.

---

## Keyboard Shortcuts

| Key | Action |
|---|---|
| **⌘K** / **Ctrl+K** | Open the suite-wide search modal. |

---

## Support

- **Email** — info@docklabs.ai (1–2 business day response).
- **Feedback widget** — bottom-right corner of every page; routes to the
  shared support queue.
- **Per-product help** — for questions specific to Helm, Harbor,
  Admiralty, etc., open the help link inside that product.

---

*Last updated: 2026-04-30.*
