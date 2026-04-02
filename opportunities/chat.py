"""AI-powered federal grant discovery chat."""
from keel.search.chat import SearchChat

from .search import GrantSearchEngine

EXTRACT_PROMPT = """Extract search keywords from this question about federal grants. Return ONLY a JSON object.

Format: {"query": "search terms", "agency": null, "status": null}

Examples:
- "What NSF grants are available for climate research?" → {"query": "climate research", "agency": "U.S. National Science Foundation", "status": null}
- "Show me posted EPA environmental grants" → {"query": "environmental", "agency": "Environmental Protection Agency", "status": "posted"}
- "Infrastructure funding opportunities" → {"query": "infrastructure funding", "agency": null, "status": null}
- "Hi, what can you do?" → {"query": "", "agency": null, "status": null}

Status values: posted, forecasted, closed, archived

User question: """

EXPLAIN_PROMPT = """You are Bounty, a federal grants intelligence assistant.

CRITICAL RULES:
- You may ONLY reference grants listed in the SEARCH RESULTS below. Do NOT mention any grants not in this list.
- Use ONLY the title, agency, status, funding range, and deadline shown in the results.
- If you are unsure about something, say so. Never fabricate grant details.
- Do NOT suggest specific grants that aren't in the results.

The user asked: "{question}"
Search query used: "{query}"

SEARCH RESULTS ({count} grants found):
{results}

Respond conversationally. Reference grants by title. Group by agency or theme if helpful. Mention deadlines that are approaching. Suggest related search terms. Use markdown formatting. Be concise."""

NO_RESULTS_PROMPT = """You are Bounty, a federal grants intelligence assistant.

The user asked: "{question}"
You searched for "{query}" but found NO matching grants in the database.

CRITICAL: Do NOT make up or suggest specific grant names or numbers.

Respond helpfully: suggest alternative search terms (agencies may use different terminology), and offer to try different keywords. Be concise."""

GREETING_PROMPT = """You are Bounty, a federal grants intelligence assistant. You help users discover federal funding opportunities from Grants.gov.

The user said: "{question}"

This doesn't seem to be a search query. Respond conversationally, explain what you can do (search ~1,700 federal grants by keyword, agency, funding level, etc.), and suggest example questions. Be concise.

CRITICAL: Do NOT mention any specific grant names or numbers."""


class GrantChat(SearchChat):
    """AI chat for federal grant discovery."""

    engine = GrantSearchEngine()
    extract_prompt = EXTRACT_PROMPT
    explain_prompt = EXPLAIN_PROMPT
    no_results_prompt = NO_RESULTS_PROMPT
    greeting_prompt = GREETING_PROMPT

    def format_result_for_frontend(self, result):
        """Format a FederalOpportunity for the chat results panel."""
        return {
            'id': result.pk,
            'title': result.title[:120],
            'agency': result.agency_name,
            'status': result.get_opportunity_status_display(),
            'close_date': str(result.close_date) if result.close_date else '',
            'funding': result.funding_range_display,
            'url': f'/opportunities/{result.pk}/',
        }

    def format_results_for_prompt(self, results):
        """Format grants as text for Claude's explain prompt."""
        lines = []
        for r in results:
            lines.append(
                f"  - Title: {r.title}\n"
                f"    Agency: {r.agency_name}\n"
                f"    Status: {r.get_opportunity_status_display()}\n"
                f"    Funding: {r.funding_range_display}\n"
                f"    Deadline: {r.close_date or 'Not specified'}\n"
                f"    Number: {r.opportunity_number or 'N/A'}"
            )
        return "\n".join(lines)
