from keel.core.workflow import Transition, WorkflowEngine

TRACKED_OPPORTUNITY_WORKFLOW = WorkflowEngine(
    transitions=[
        # Forward progression
        Transition('watching', 'preparing', roles=['any'], label='Start Preparing'),
        # Internal approval gate — fires the Manifest signing handoff. The
        # preparing→applied direct path stays available for cases where no
        # internal approval is required, but `preparing → approved → applied`
        # is the canonical path when signatures are needed.
        Transition('preparing', 'approved', roles=['any'], label='Mark Internally Approved'),
        Transition('approved', 'applied', roles=['any'], label='Mark Applied'),
        Transition('preparing', 'applied', roles=['any'], label='Mark Applied (no approval)'),
        Transition('applied', 'awarded', roles=['any'], label='Mark Awarded'),
        Transition('applied', 'declined', roles=['any'], label='Mark Declined'),
        # Backward / lateral
        Transition('preparing', 'watching', roles=['any'], label='Back to Watching'),
        Transition('approved', 'preparing', roles=['any'], label='Back to Preparing'),
        # Direct from watching
        Transition('watching', 'declined', roles=['any'], label='Decline'),
    ],
    history_model='opportunities.TrackedOpportunityStatusHistory',
    history_fk_field='tracked_opportunity',
)
