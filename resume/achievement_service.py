from assessment.models import AssessmentAttempt

from .models import ResumeAchievement


def sync_verified_learning_achievements(user):
    """
    Creates or updates verified CognifyAI achievements.

    Current rule:
    - Only Advanced assessments can become verified achievements.
    - Score must be exactly 100%.
    - Only the latest assessment for each subject + topic is considered.
    - Easy and Medium assessments never become resume achievements.
    - Existing achievements are updated instead of duplicated.
    """

    attempts = (
        AssessmentAttempt.objects
        .filter(user=user)
        .order_by("-created_at")
    )

    latest_attempts = {}

    for attempt in attempts:

        subject = attempt.subject.strip()
        topic = attempt.topic.strip()

        key = (
            subject.lower(),
            topic.lower()
        )

        if key not in latest_attempts:
            latest_attempts[key] = attempt

    verified_count = 0

    for key, attempt in latest_attempts.items():

        subject = attempt.subject.strip()
        topic = attempt.topic.strip()
        difficulty = attempt.difficulty.strip().lower()

        source_reference = (
            f"ASSESSMENT:{subject}:{topic}"
        )

        achievement = (
            ResumeAchievement.objects
            .filter(
                user=user,
                source="ASSESSMENT",
                source_reference=source_reference
            )
            .first()
        )

        # =====================================================
        # ONLY ADVANCED + 100% CAN BECOME VERIFIED
        # =====================================================

        if difficulty == "advanced" and attempt.score >= 100:

            title = topic

            description = (
                f"Demonstrated 100% mastery in "
                f"{topic} at the Advanced level "
                f"through CognifyAI."
            )

            if achievement:

                achievement.title = title
                achievement.description = description
                achievement.verified = True

                achievement.save(
                    update_fields=[
                        "title",
                        "description",
                        "verified",
                    ]
                )

            else:

                ResumeAchievement.objects.create(
                    user=user,
                    title=title,
                    description=description,
                    source="ASSESSMENT",
                    verified=True,
                    source_reference=source_reference,
                )

            verified_count += 1

        else:

            # -------------------------------------------------
            # If the latest result no longer qualifies,
            # remove its verified status.
            # -------------------------------------------------

            if achievement and achievement.verified:

                achievement.verified = False

                achievement.save(
                    update_fields=[
                        "verified"
                    ]
                )

    return verified_count


def get_verified_learning_achievements(user):
    """
    Returns only currently verified CognifyAI achievements.
    """

    sync_verified_learning_achievements(user)

    return (
        ResumeAchievement.objects
        .filter(
            user=user,
            source="ASSESSMENT",
            verified=True,
        )
        .order_by("-created_at")
    )