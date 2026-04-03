from keel.core.workflow import Transition, WorkflowEngine

TRACKED_OPPORTUNITY_WORKFLOW = WorkflowEngine(
    transitions=[
        # Forward progression
        Transition('watching', 'preparing', roles=['any'], label='Start Preparing'),
        Transition('preparing', 'applied', roles=['any'], label='Mark Applied'),
        Transition('applied', 'awarded', roles=['any'], label='Mark Awarded'),
        Transition('applied', 'declined', roles=['any'], label='Mark Declined'),
        # Backward / lateral
        Transition('preparing', 'watching', roles=['any'], label='Back to Watching'),
        # Direct from watching
        Transition('watching', 'declined', roles=['any'], label='Decline'),
    ],
    history_model='opportunities.TrackedOpportunityStatusHistory',
    history_fk_field='tracked_opportunity',
)
