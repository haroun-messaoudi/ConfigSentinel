import re


def score_diff(diff_text: str, detection_profile):
    """
    Checks every tracked concept in the device's profile against the diff.
    Returns (highest_severity_class, [all_matched_concepts]) — ([], None) if
    the device has no profile, or (None, []) if nothing matched.
    """
    if detection_profile is None:
        return None, []

    concepts = (
        detection_profile.tracked_concepts
        .select_related("severity_class")
        .order_by("-severity_class__rank")
    )

    matched = [c for c in concepts if re.search(c.pattern, diff_text, re.MULTILINE)]

    if not matched:
        return None, []

    highest_severity = matched[0].severity_class  # first = highest rank, since queryset is pre-sorted
    return highest_severity, matched