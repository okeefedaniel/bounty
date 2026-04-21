"""Backfill OpportunityAssignment records for existing tracked opportunities.

For every existing TrackedOpportunity whose ``tracked_by`` is set, we
record an implicit self-claim so the assignment history is complete
going forward. Without this, existing opportunities would appear
unclaimed in views that rely on the assignments relation.
"""
from django.db import migrations


def backfill(apps, schema_editor):
    TrackedOpportunity = apps.get_model('opportunities', 'TrackedOpportunity')
    OpportunityAssignment = apps.get_model('opportunities', 'OpportunityAssignment')

    to_create = []
    for tracked in TrackedOpportunity.objects.filter(tracked_by__isnull=False).iterator():
        to_create.append(OpportunityAssignment(
            tracked_opportunity=tracked,
            assigned_to=tracked.tracked_by,
            assigned_by=None,
            assignment_type='claimed',
            status='in_progress',
            claimed_at=tracked.created_at,
        ))
    if to_create:
        OpportunityAssignment.objects.bulk_create(to_create)


def reverse(apps, schema_editor):
    OpportunityAssignment = apps.get_model('opportunities', 'OpportunityAssignment')
    OpportunityAssignment.objects.all().delete()


class Migration(migrations.Migration):

    dependencies = [
        ('opportunities', '0005_alter_opportunitycollaborator_options_and_more'),
    ]

    operations = [
        migrations.RunPython(backfill, reverse),
    ]
