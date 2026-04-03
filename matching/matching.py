"""
AI-powered federal grant matching using the Anthropic Claude API.

Scores federal opportunities against user preferences and returns a
relevance score (0-100) plus a short explanation.
"""
import json
import logging
import threading

from django.conf import settings
from django.utils import timezone

logger = logging.getLogger(__name__)

MODEL = 'claude-sonnet-4-20250514'
MAX_TOKENS = 250


def build_preference_context(preference, state_preference=None):
    """Format merged state + user preferences into a text block for the AI prompt."""
    from matching.models import FocusArea

    user = preference.user
    parts = []
    parts.append(f"Role: {user.get_role_display()}")
    if user.organization_name:
        parts.append(f"Organization: {user.organization_name}")

    # Merge focus areas: state-wide + user-level
    all_focus_areas = set(preference.focus_areas or [])
    if state_preference and state_preference.focus_areas:
        all_focus_areas.update(state_preference.focus_areas)

    if all_focus_areas:
        area_labels = dict(FocusArea.choices)
        areas = [str(area_labels.get(a, a)) for a in sorted(all_focus_areas)]
        parts.append(f"Focus Areas: {', '.join(areas)}")

    # Merge keywords: state-wide + user-level
    all_keywords = list(preference.keywords or [])
    if state_preference and state_preference.keywords:
        all_keywords = list(state_preference.keywords) + all_keywords
    if all_keywords:
        unique_keywords = list(dict.fromkeys(all_keywords))  # dedupe preserving order
        parts.append(f"Keywords: {', '.join(unique_keywords)}")

    # Funding range: use user override if set, else fall back to state
    funding_min = preference.funding_range_min
    funding_max = preference.funding_range_max
    if state_preference:
        if not funding_min and state_preference.funding_range_min:
            funding_min = state_preference.funding_range_min
        if not funding_max and state_preference.funding_range_max:
            funding_max = state_preference.funding_range_max

    if funding_min or funding_max:
        low = f"${funding_min:,.0f}" if funding_min else "any"
        high = f"${funding_max:,.0f}" if funding_max else "any"
        parts.append(f"Funding Range: {low} – {high}")

    # Merge descriptions
    descriptions = []
    if state_preference and state_preference.description:
        descriptions.append(f"State Priorities: {state_preference.description}")
    if preference.description:
        descriptions.append(f"User Priorities: {preference.description}")
    if descriptions:
        parts.extend(descriptions)

    return '\n'.join(parts)


def build_opportunity_summary(opportunity):
    """Format a FederalOpportunity into a text block."""
    parts = []
    parts.append(f"Title: {opportunity.title}")
    parts.append(f"Agency: {opportunity.agency_name}")
    if opportunity.category:
        parts.append(f"Category: {opportunity.category}")
    if opportunity.description:
        parts.append(f"Description: {opportunity.description[:2000]}")
    if opportunity.funding_range_display:
        parts.append(f"Funding: {opportunity.funding_range_display}")
    if opportunity.eligible_applicants:
        parts.append(f"Eligibility: {opportunity.eligible_applicants[:500]}")
    if opportunity.applicant_types:
        parts.append(f"Applicant Types: {', '.join(str(t) for t in opportunity.applicant_types)}")
    if opportunity.close_date:
        parts.append(f"Close Date: {opportunity.close_date}")
    parts.append("Source: Federal (Grants.gov)")
    return '\n'.join(parts)


def score_opportunity(preference, opportunity, state_preference=None):
    """Call the Claude API to score an opportunity against user preferences."""
    api_key = preference.user.get_anthropic_api_key() or getattr(settings, 'ANTHROPIC_API_KEY', '')
    if not api_key:
        logger.warning('No API key for user %s — skipping AI scoring', preference.user)
        return None

    from keel.core.ai import get_client, call_claude

    pref_context = build_preference_context(preference, state_preference)
    opp_summary = build_opportunity_summary(opportunity)

    system = (
        "You are an AI assistant helping a federal grant coordinator identify "
        "federal grant opportunities they should track and pursue. Score how "
        "relevant the opportunity is for the coordinator's strategic priorities."
    )

    user_message = (
        "Score the following opportunity for this user on a scale of 0–100.\n\n"
        "=== USER PROFILE ===\n"
        f"{pref_context}\n\n"
        "=== OPPORTUNITY ===\n"
        f"{opp_summary}\n\n"
        "Respond with ONLY a JSON object (no markdown, no explanation outside "
        "the JSON). The JSON must have exactly two keys:\n"
        '  "score": integer 0-100\n'
        '  "explanation": string (1-2 sentences explaining the score)\n'
    )

    try:
        client = get_client(api_key=api_key)
        text = call_claude(
            client, system=system, user_message=user_message,
            model=MODEL, max_tokens=MAX_TOKENS,
        )
        if text is None:
            return None
        text = text.strip()

        if text.startswith('```'):
            text = text.split('\n', 1)[-1].rsplit('```', 1)[0].strip()

        result = json.loads(text)
        score = int(result.get('score', 0))
        explanation = str(result.get('explanation', ''))
        return {'score': max(0, min(100, score)), 'explanation': explanation}

    except json.JSONDecodeError as exc:
        logger.warning('AI returned invalid JSON: %s', exc)
        return None
    except Exception as exc:
        logger.exception('AI scoring failed: %s', exc)
        return None


def run_matching_for_user(user):
    """Score open federal opportunities against user's active preferences."""
    from keel.notifications import notify
    from matching.models import MatchPreference, OpportunityMatch, StatePreference
    from opportunities.models import FederalOpportunity

    if not getattr(user, 'anthropic_api_key', '') and not getattr(settings, 'ANTHROPIC_API_KEY', ''):
        return {'scored': 0, 'stored': 0, 'notified': 0}

    min_score = getattr(settings, 'GRANT_MATCH_MIN_SCORE', 60)
    notify_score = getattr(settings, 'GRANT_MATCH_NOTIFY_SCORE', 75)
    high_score = getattr(settings, 'GRANT_MATCH_HIGH_SCORE', 90)

    try:
        pref = MatchPreference.objects.select_related('user').get(user=user, is_active=True)
    except MatchPreference.DoesNotExist:
        return {'scored': 0, 'stored': 0, 'notified': 0}

    # Load state-wide preferences (merged into AI context)
    state_pref = StatePreference.get_active()

    federal_opps = list(
        FederalOpportunity.objects.filter(
            opportunity_status=FederalOpportunity.OpportunityStatus.POSTED,
        ).order_by('-post_date')[:200]
    )

    existing_ids = set(
        OpportunityMatch.objects.filter(user=user)
        .values_list('federal_opportunity_id', flat=True)
    )

    scored = stored = notified = 0

    for opp in federal_opps:
        if opp.pk in existing_ids:
            continue

        result = score_opportunity(pref, opp, state_preference=state_pref)
        scored += 1

        if result is None:
            continue

        score = result['score']
        explanation = result['explanation']

        if score < min_score:
            continue

        match_obj = OpportunityMatch.objects.create(
            user=user,
            federal_opportunity=opp,
            relevance_score=score,
            explanation=explanation,
        )
        stored += 1

        if score >= notify_score:
            title_text = match_obj.opportunity_title
            opp_url = match_obj.opportunity_url

            # Choose event type based on score
            event = 'grant_match_high_score' if score >= high_score else 'grant_match_found'

            notify(
                event=event,
                recipients=[user],
                title='New Grant Recommendation',
                message=f'We found a {score}% match: "{title_text[:80]}". {explanation[:120]}',
                link=opp_url,
                priority='high' if score >= high_score else 'medium',
                context={
                    'user': user,
                    'match': match_obj,
                    'title': title_text,
                    'score': score,
                    'explanation': explanation,
                },
            )

            match_obj.notified = True
            match_obj.notified_at = timezone.now()
            match_obj.save(update_fields=['notified', 'notified_at'])
            notified += 1

    logger.info('Matching complete for %s: scored=%d stored=%d notified=%d',
                user.username, scored, stored, notified)
    return {'scored': scored, 'stored': stored, 'notified': notified}


def run_matching_async(user):
    """Fire-and-forget: run matching in a background thread."""
    import django

    def _worker():
        try:
            django.db.connections.close_all()
            result = run_matching_for_user(user)
            logger.info('Background matching completed for %s: %s', user.username, result)
        except Exception:
            logger.exception('Background matching failed for %s', user)
        finally:
            django.db.connections.close_all()

    thread = threading.Thread(target=_worker, daemon=True, name=f'match-{user.username}')
    thread.start()
