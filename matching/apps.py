from django.apps import AppConfig


class MatchingConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'matching'

    def ready(self):
        from keel.notifications import NotificationType, register

        register(NotificationType(
            key='grant_match_found',
            label='New Grant Recommendation',
            description='An AI-matched federal grant opportunity scored above your threshold.',
            category='AI Matching',
            default_channels=['in_app', 'email'],
            default_roles=['admin', 'coordinator', 'analyst'],
            priority='medium',
            email_template='emails/grant_match.html',
            email_subject='Grant Recommendation: {title}',
        ))

        register(NotificationType(
            key='grant_match_high_score',
            label='High-Score Grant Match',
            description='A federal grant opportunity scored very highly against your preferences.',
            category='AI Matching',
            default_channels=['in_app', 'email'],
            default_roles=['admin', 'coordinator'],
            priority='high',
            email_template='emails/grant_match.html',
            email_subject='High-Score Match: {title}',
        ))

        register(NotificationType(
            key='grant_digest',
            label='Match Digest',
            description='A periodic summary of new AI-matched grant opportunities.',
            category='AI Matching',
            default_channels=['email'],
            default_roles=[],
            priority='low',
            email_template='emails/grant_digest.html',
            email_subject='Bounty Digest: {count} New Matches',
            allow_mute=True,
        ))
