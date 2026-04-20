from django.apps import AppConfig


class CoreConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'core'
    label = 'bounty_core'
    verbose_name = 'Bounty Core'

    def ready(self):
        # Register Bounty models for signal-based audit logging
        from keel.core.audit_signals import register_audited_model, connect_audit_signals

        # Opportunities
        register_audited_model('opportunities.FederalOpportunity', 'Federal Opportunity')
        register_audited_model('opportunities.OpportunityCollaborator', 'Opportunity Collaborator')
        # Matching
        register_audited_model('matching.MatchPreference', 'Match Preference')
        register_audited_model('matching.OpportunityMatch', 'Opportunity Match')
        register_audited_model('matching.StatePreference', 'State Preference')
        # Integration
        register_audited_model('integration.HarborConnection', 'Harbor Connection')
        register_audited_model('integration.TrackedOpportunity', 'Tracked Opportunity')

        connect_audit_signals()
