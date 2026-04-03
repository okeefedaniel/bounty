"""
Seed Bounty with realistic demo data.

Run with:  python manage.py shell < seed_data.py

Creates a demo environment with federal opportunities, tracked
opportunities, collaborators, and AI match preferences.
"""
import os
import sys
from datetime import date, timedelta
from decimal import Decimal

import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'bounty.settings')
django.setup()

from django.utils import timezone

from allauth.account.models import EmailAddress
from django.contrib.auth import get_user_model
User = get_user_model()
from matching.models import MatchPreference, OpportunityMatch
from opportunities.models import (
    FederalOpportunity,
    OpportunityCollaborator,
    TrackedOpportunity,
)

now = timezone.now()

# ── Users (password: demo2026!) ──────────────────────────────
print("Creating users...")


from keel.accounts.models import ProductAccess
from core.models import BountyProfile

PRODUCT = 'bounty'


def make_user(username, first, last, role, email, org_name=''):
    u, created = User.objects.get_or_create(
        username=username,
        defaults=dict(
            first_name=first, last_name=last,
            email=email,
        ),
    )
    if created:
        u.set_password('demo2026!')
        u.save()
    # Create/update ProductAccess for role
    ProductAccess.objects.update_or_create(
        user=u, product=PRODUCT,
        defaults={'role': role, 'is_active': True},
    )
    # Create BountyProfile for org_name
    if org_name:
        profile, _ = BountyProfile.objects.get_or_create(user=u)
        profile.organization_name = org_name
        profile.save(update_fields=['organization_name'])
    if email:
        EmailAddress.objects.get_or_create(
            user=u, email=email,
            defaults={'verified': True, 'primary': True},
        )
    return u


# System Admin (also the Django superuser)
admin_user = User.objects.filter(username='admin').first()
if admin_user:
    admin_user.first_name = 'System'
    admin_user.last_name = 'Administrator'
    admin_user.save()
    ProductAccess.objects.update_or_create(
        user=admin_user, product=PRODUCT,
        defaults={'role': 'admin', 'is_active': True},
    )
    if admin_user.email:
        EmailAddress.objects.get_or_create(
            user=admin_user, email=admin_user.email,
            defaults={'verified': True, 'primary': True},
        )

coordinator = make_user(
    'coordinator', 'Federal', 'Coordinator', 'coordinator',
    'coordinator@dok.gov', 'Office of Budget & Management',
)
analyst = make_user(
    'analyst', 'Grant', 'Analyst', 'analyst',
    'analyst@dok.gov', 'Office of Budget & Management',
)
viewer = make_user(
    'viewer', 'Policy', 'Viewer', 'viewer',
    'viewer@dok.gov', 'Office of Budget & Management',
)

# Additional staff for collaborator demos
mike = make_user(
    'mike.johnson', 'Mike', 'Johnson', 'coordinator',
    'mike.johnson@dok.gov', 'Dept of Environmental Protection',
)
sarah = make_user(
    'sarah.chen', 'Sarah', 'Chen', 'analyst',
    'sarah.chen@dok.gov', 'Dept of Transportation',
)
lisa = make_user(
    'lisa.park', 'Lisa', 'Park', 'coordinator',
    'lisa.park@dok.gov', 'Dept of Housing',
)

print(f"  Users: {User.objects.count()}")


# ── Federal Opportunities (demo data) ────────────────────────
print("Creating demo federal opportunities...")
federal_opps_data = [
    {
        "opp_id": "350994", "opp_num": "HHS-2026-ACF-OCC-YD-0042",
        "title": "Youth Development Community Partnerships",
        "desc": "Grants to support the development of community partnerships that promote positive youth development outcomes for underserved youth ages 12-24 through evidence-based programming.",
        "agency_name": "Administration for Children and Families",
        "agency_code": "HHS-ACF", "category": "Discretionary",
        "instrument": "grant", "cfda": ["93.590"],
        "floor": 100000, "ceiling": 500000, "total": 15000000,
        "expected": 30, "post_days": -30, "close_days": 45,
        "status": "posted", "applicants": ["State governments", "County governments", "Nonprofits"],
    },
    {
        "opp_id": "351127", "opp_num": "EPA-OLEM-OBLR-26-03",
        "title": "Brownfields Assessment and Cleanup Cooperative Agreements",
        "desc": "EPA is soliciting applications for Brownfields Assessment and Cleanup cooperative agreements for communities, states, and tribes to assess and clean up contaminated brownfield properties.",
        "agency_name": "Environmental Protection Agency",
        "agency_code": "EPA", "category": "Discretionary",
        "instrument": "cooperative_agreement", "cfda": ["66.818"],
        "floor": 200000, "ceiling": 2000000, "total": 60000000,
        "expected": 80, "post_days": -20, "close_days": 60,
        "status": "posted", "applicants": ["State governments", "County governments", "City or township governments", "Nonprofits"],
    },
    {
        "opp_id": "351455", "opp_num": "DOT-FHWA-2026-RAISE",
        "title": "RAISE Transportation Discretionary Grants",
        "desc": "The RAISE program provides competitive grants for surface transportation infrastructure projects that will have a significant local or regional impact on safety, environmental sustainability, and economic competitiveness.",
        "agency_name": "Department of Transportation",
        "agency_code": "DOT", "category": "Discretionary",
        "instrument": "grant", "cfda": ["20.933"],
        "floor": 5000000, "ceiling": 25000000, "total": 2200000000,
        "expected": 200, "post_days": -45, "close_days": 30,
        "status": "posted", "applicants": ["State governments", "County governments", "City or township governments"],
    },
    {
        "opp_id": "351002", "opp_num": "ED-GRANTS-2026-STEMGROW",
        "title": "STEM Education Growth Initiative",
        "desc": "Supports innovative approaches to improving STEM education outcomes, with emphasis on expanding access for underrepresented populations in science, technology, engineering, and mathematics fields.",
        "agency_name": "Department of Education",
        "agency_code": "ED", "category": "Discretionary",
        "instrument": "grant", "cfda": ["84.305A"],
        "floor": 250000, "ceiling": 1500000, "total": 45000000,
        "expected": 50, "post_days": -60, "close_days": -15,
        "status": "closed", "applicants": ["State governments", "Educational institutions", "Nonprofits"],
    },
    {
        "opp_id": "350888", "opp_num": "HUD-2026-CPD-CDBG-DR",
        "title": "Community Development Block Grant - Disaster Recovery",
        "desc": "Provides flexible grants to help cities, counties, and states recover from presidentially declared disasters, with focus on housing, infrastructure, and economic revitalization in affected areas.",
        "agency_name": "Department of Housing and Urban Development",
        "agency_code": "HUD", "category": "Discretionary",
        "instrument": "grant", "cfda": ["14.218", "14.228"],
        "floor": 1000000, "ceiling": 50000000, "total": 500000000,
        "expected": 25, "post_days": -90, "close_days": 90,
        "status": "posted", "applicants": ["State governments", "County governments", "City or township governments"],
    },
]

federal_opps = {}
for fd in federal_opps_data:
    post_d = date.today() + timedelta(days=fd["post_days"])
    close_d = date.today() + timedelta(days=fd["close_days"])
    fopp, _ = FederalOpportunity.objects.get_or_create(
        opportunity_id=fd["opp_id"],
        defaults=dict(
            opportunity_number=fd["opp_num"],
            title=fd["title"],
            description=fd["desc"],
            agency_name=fd["agency_name"],
            agency_code=fd["agency_code"],
            category=fd["category"],
            funding_instrument=fd["instrument"],
            cfda_numbers=fd["cfda"],
            award_floor=Decimal(str(fd["floor"])),
            award_ceiling=Decimal(str(fd["ceiling"])),
            total_funding=Decimal(str(fd["total"])),
            expected_awards=fd["expected"],
            post_date=post_d,
            close_date=close_d,
            opportunity_status=fd["status"],
            applicant_types=fd["applicants"],
            eligible_applicants="See full opportunity listing on Grants.gov for complete eligibility details.",
            grants_gov_url=f"https://simpler.grants.gov/opportunity/{fd['opp_id']}",
        ),
    )
    federal_opps[fd["opp_id"]] = fopp

print(f"  Federal Opportunities: {FederalOpportunity.objects.count()}")


# ── Tracked Opportunities (Coordinator's pipeline) ───────────
print("Creating tracked federal opportunities...")
tracked_data = [
    {
        "opp": "351127", "status": "preparing", "priority": "high",
        "notes": "EPA Brownfields — aligns with DEEP priorities. Meeting scheduled with DEEP Commissioner's office next week to discuss state match strategy.",
    },
    {
        "opp": "351455", "status": "watching", "priority": "high",
        "notes": "RAISE grants — DOT is interested. Need to coordinate with state DOT on which projects to put forward. Capital City busway expansion is leading candidate.",
    },
    {
        "opp": "350994", "status": "watching", "priority": "medium",
        "notes": "Youth Development — DCF may be interested. Reached out to Deputy Commissioner's office.",
    },
    {
        "opp": "351002", "status": "declined", "priority": "low",
        "notes": "Deadline passed. We did not have a strong enough multi-agency consortium ready in time. Consider for next funding cycle.",
    },
    {
        "opp": "350888", "status": "preparing", "priority": "high",
        "notes": "CDBG-DR — Critical for post-storm recovery in coastal towns. DOH is taking the lead; coordinating with DCD on economic revitalization component.",
    },
]

tracked_records = {}
for td in tracked_data:
    tr, _ = TrackedOpportunity.objects.get_or_create(
        federal_opportunity=federal_opps[td["opp"]],
        tracked_by=coordinator,
        defaults=dict(
            status=td["status"],
            priority=td["priority"],
            notes=td["notes"],
        ),
    )
    tracked_records[td["opp"]] = tr

print(f"  Tracked Opportunities: {TrackedOpportunity.objects.count()}")


# ── Collaborators on tracked opportunities ────────────────────
print("Creating opportunity collaborators...")
# EPA Brownfields — DEEP staff + external EPA liaison
epa_tracked = tracked_records["351127"]
OpportunityCollaborator.objects.get_or_create(
    tracked_opportunity=epa_tracked, user=mike,
    defaults=dict(role='contributor', invited_by=coordinator),
)
OpportunityCollaborator.objects.get_or_create(
    tracked_opportunity=epa_tracked, email='j.martinez@epa.gov',
    defaults=dict(
        name='Jorge Martinez', role='observer',
        invited_by=coordinator,
    ),
)

# RAISE — DOT staff internal
raise_tracked = tracked_records["351455"]
OpportunityCollaborator.objects.get_or_create(
    tracked_opportunity=raise_tracked, user=sarah,
    defaults=dict(role='reviewer', invited_by=coordinator),
)

# CDBG-DR — DOH staff + external HUD contact
cdbg_tracked = tracked_records["350888"]
OpportunityCollaborator.objects.get_or_create(
    tracked_opportunity=cdbg_tracked, user=lisa,
    defaults=dict(role='contributor', invited_by=coordinator),
)
OpportunityCollaborator.objects.get_or_create(
    tracked_opportunity=cdbg_tracked, email='r.thompson@hud.gov',
    defaults=dict(
        name='Regina Thompson', role='observer',
        invited_by=coordinator,
    ),
)

print(f"  Collaborators: {OpportunityCollaborator.objects.count()}")


# ── AI Match Preferences ─────────────────────────────────────
print("Creating match preferences...")
MatchPreference.objects.get_or_create(
    user=coordinator,
    defaults=dict(
        focus_areas=[
            'Environmental Remediation', 'Infrastructure',
            'Housing', 'Economic Development', 'Disaster Recovery',
        ],
        funding_range_min=Decimal('100000'),
        funding_range_max=Decimal('50000000'),
        description=(
            "State government seeking federal funding for environmental cleanup, "
            "infrastructure improvements, housing programs, and disaster recovery "
            "initiatives. Priority on opportunities that support underserved "
            "communities and align with state strategic priorities."
        ),
        is_active=True,
    ),
)

MatchPreference.objects.get_or_create(
    user=analyst,
    defaults=dict(
        focus_areas=[
            'Education', 'Youth Development', 'STEM',
            'Workforce Development',
        ],
        funding_range_min=Decimal('50000'),
        funding_range_max=Decimal('5000000'),
        description=(
            "Researching federal funding opportunities in education and "
            "workforce development for state agency partners."
        ),
        is_active=True,
    ),
)

print(f"  Match Preferences: {MatchPreference.objects.count()}")


# ── Demo AI Matches ──────────────────────────────────────────
print("Creating demo AI matches...")
OpportunityMatch.objects.get_or_create(
    user=coordinator,
    federal_opportunity=federal_opps["351127"],
    defaults=dict(
        relevance_score=92,
        explanation="Strong alignment with environmental remediation priorities. EPA Brownfields program directly supports state DEEP cleanup goals and targets underserved communities.",
        status='new',
    ),
)
OpportunityMatch.objects.get_or_create(
    user=coordinator,
    federal_opportunity=federal_opps["350888"],
    defaults=dict(
        relevance_score=88,
        explanation="Excellent match for disaster recovery and housing needs. CDBG-DR funding aligns with post-storm coastal recovery priorities.",
        status='new',
    ),
)
OpportunityMatch.objects.get_or_create(
    user=coordinator,
    federal_opportunity=federal_opps["351455"],
    defaults=dict(
        relevance_score=78,
        explanation="Good match for infrastructure priorities. RAISE grants support the Capital City busway expansion project under consideration.",
        status='viewed',
    ),
)
OpportunityMatch.objects.get_or_create(
    user=analyst,
    federal_opportunity=federal_opps["350994"],
    defaults=dict(
        relevance_score=85,
        explanation="Strong alignment with youth development and education focus areas. Supports evidence-based programming for underserved youth.",
        status='new',
    ),
)

print(f"  AI Matches: {OpportunityMatch.objects.count()}")


# ── Summary ──────────────────────────────────────────────────
print("\n=== Bounty Seed Data Complete ===")
print(f"  Users:              {User.objects.count()}")
print(f"  Federal Opps:       {FederalOpportunity.objects.count()}")
print(f"  Tracked Opps:       {TrackedOpportunity.objects.count()}")
print(f"  Collaborators:      {OpportunityCollaborator.objects.count()}")
print(f"  Match Preferences:  {MatchPreference.objects.count()}")
print(f"  AI Matches:         {OpportunityMatch.objects.count()}")
print("\nDemo credentials: all users use password 'demo2026!'")
print("Roles: coordinator, analyst, viewer, admin")
