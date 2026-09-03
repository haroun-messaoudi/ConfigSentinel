from django.test import TestCase
from devices.models import SeverityClass, TrackedConcept, DetectionProfile
from devices.risk import score_diff


class ScoreDiffTests(TestCase):

    def setUp(self):
        self.low, _ = SeverityClass.objects.get_or_create(name="Low", defaults={"rank": 10})
        self.medium, _ = SeverityClass.objects.get_or_create(name="Medium", defaults={"rank": 20})
        self.high, _ = SeverityClass.objects.get_or_create(name="High", defaults={"rank": 30})

        self.acl_concept = TrackedConcept.objects.create(
            name="ACL Change Test",
            pattern=r"access-list",
            severity_class=self.high,
            source="CUSTOM",
        )
        self.hostname_concept = TrackedConcept.objects.create(
            name="Hostname Change Test",
            pattern=r"hostname",
            severity_class=self.low,
            source="CUSTOM",
        )

        self.profile = DetectionProfile.objects.create(name="Test Profile")
        self.profile.tracked_concepts.set([self.acl_concept, self.hostname_concept])

    def test_no_profile_returns_no_match(self):
        severity, matched = score_diff("access-list 10 permit any", detection_profile=None)
        self.assertIsNone(severity)
        self.assertEqual(matched, [])

    def test_single_concept_match(self):
        diff_text = "+access-list 10 permit 192.168.1.0/24"
        severity, matched = score_diff(diff_text, self.profile)

        self.assertEqual(severity, self.high)
        self.assertEqual(matched, [self.acl_concept])

    def test_no_match_when_nothing_relevant_changed(self):
        diff_text = "+description uplink to core switch"
        severity, matched = score_diff(diff_text, self.profile)

        self.assertIsNone(severity)
        self.assertEqual(matched, [])

    def test_multiple_concepts_match_and_highest_severity_wins(self):
        diff_text = "+access-list 10 permit any\n+hostname r1-renamed"
        severity, matched = score_diff(diff_text, self.profile)

        # Both concepts matched — this is the exact multi-match fix from
        # yesterday. If it regresses back to "first match only", this fails.
        self.assertEqual(len(matched), 2)
        self.assertIn(self.acl_concept, matched)
        self.assertIn(self.hostname_concept, matched)

        # Highest-ranked severity among matches must win, not just the
        # first one found.
        self.assertEqual(severity, self.high)