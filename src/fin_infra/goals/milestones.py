"""
Milestone tracking for financial goals.

Provides milestone management with:
- Add/update milestones to goals
- Automatic milestone detection and celebration
- Webhook notifications when milestones reached
- Progress tracking with milestone history

Example:
    from fin_infra.goals.milestones import add_milestone, check_milestones
    from datetime import datetime

    # Add milestone
    milestone = add_milestone(
        goal_id="goal_123",
        amount=25000.0,
        target_date=datetime(2026, 6, 1),
        description="25% to emergency fund target"
    )

    # Check which milestones have been reached
    reached = check_milestones("goal_123")
    for m in reached:
        print(f"🎉 Milestone reached: {m['description']}")
"""

from datetime import datetime
from typing import Any

from fin_infra.goals.management import get_goal, update_goal
from fin_infra.goals.models import Milestone


# ============================================================================
# Milestone Management
# ============================================================================


def add_milestone(
    goal_id: str,
    amount: float,
    description: str,
    target_date: datetime | None = None,
) -> dict[str, Any]:
    """
    Add a milestone to a goal.

    Args:
        goal_id: Goal identifier
        amount: Milestone target amount
        description: Milestone description
        target_date: Optional target date to reach milestone

    Returns:
        Milestone dict

    Raises:
        KeyError: If goal not found
        ValueError: If milestone amount invalid

    Example:
        from fin_infra.goals.milestones import add_milestone
        from datetime import datetime

        milestone = add_milestone(
            goal_id="goal_123",
            amount=25000.0,
            target_date=datetime(2026, 6, 1),
            description="25% to target"
        )
    """
    # Validate milestone
    milestone = Milestone(
        amount=amount,
        target_date=target_date,
        description=description,
        reached=False,
        reached_date=None,  # Not reached yet
    )

    # Get goal and add milestone
    goal = get_goal(goal_id)

    # Validate milestone amount is <= target
    if milestone.amount > goal["target_amount"]:
        raise ValueError(
            f"Milestone amount ({milestone.amount}) cannot exceed "
            f"goal target ({goal['target_amount']})"
        )

    # Check for duplicate milestone amounts
    for existing in goal.get("milestones", []):
        if existing["amount"] == milestone.amount:
            raise ValueError(f"Milestone at ${milestone.amount:,.0f} already exists for this goal")

    # Add to goal
    milestones = goal.get("milestones", [])
    milestones.append(milestone.model_dump())

    # Sort by amount ascending
    milestones.sort(key=lambda m: m["amount"])

    update_goal(goal_id, {"milestones": milestones})

    return milestone.model_dump()


def check_milestones(goal_id: str) -> list[dict[str, Any]]:
    """
    Check which milestones have been reached for a goal.

    Compares current_amount against milestone amounts and marks
    milestones as reached with timestamp. Returns list of newly
    reached milestones.

    Args:
        goal_id: Goal identifier

    Returns:
        List of milestone dicts that were newly reached

    Example:
        from fin_infra.goals.milestones import check_milestones

        reached = check_milestones("goal_123")
        if reached:
            print(f"🎉 {len(reached)} milestones reached!")
            for m in reached:
                print(f"   - {m['description']}: ${m['amount']:,.0f}")

    Note:
        In production, integrate with svc-infra webhooks to send
        notifications when milestones are reached:

        from svc_infra.webhooks import trigger_webhook

        for milestone in reached:
            trigger_webhook(
                event="goal.milestone_reached",
                data={
                    "goal_id": goal_id,
                    "milestone": milestone,
                    "message": get_celebration_message(milestone)
                }
            )
    """
    goal = get_goal(goal_id)
    current_amount = goal["current_amount"]

    newly_reached = []
    milestones = goal.get("milestones", [])
    updated = False

    for milestone_dict in milestones:
        milestone = Milestone(**milestone_dict)

        # Check if milestone just reached
        if not milestone.reached and current_amount >= milestone.amount:
            milestone.reached = True
            milestone.reached_date = datetime.utcnow()

            # Update dict
            milestone_dict.update(milestone.model_dump())

            newly_reached.append(milestone_dict)
            updated = True

    # Save updated milestones
    if updated:
        update_goal(goal_id, {"milestones": milestones})

    return newly_reached


def get_celebration_message(milestone: dict[str, Any]) -> str:
    """
    Generate celebration message when milestone is reached.

    Args:
        milestone: Milestone dict

    Returns:
        Celebration message string

    Example:
        message = get_celebration_message(milestone)
        # "🎉 Milestone reached! You've hit $25,000 - 25% to target!"
    """
    amount = milestone["amount"]
    description = milestone["description"]

    messages = [
        f"🎉 Milestone reached! You've hit ${amount:,.0f} - {description}!",
        f"🎊 Congratulations! ${amount:,.0f} milestone achieved - {description}",
        f"🌟 Great progress! You reached ${amount:,.0f} - {description}",
        f"💪 Keep going! ${amount:,.0f} milestone completed - {description}",
        f"🚀 Amazing! You hit ${amount:,.0f} - {description}",
    ]

    # Use amount to pick consistent message for same milestone
    index = int(amount) % len(messages)
    return messages[index]


def get_next_milestone(goal_id: str) -> dict[str, Any] | None:
    """
    Get the next unreached milestone for a goal.

    Args:
        goal_id: Goal identifier

    Returns:
        Next milestone dict or None if all reached

    Example:
        from fin_infra.goals.milestones import get_next_milestone

        next_m = get_next_milestone("goal_123")
        if next_m:
            print(f"Next milestone: ${next_m['amount']:,.0f}")
            print(f"Description: {next_m['description']}")
        else:
            print("All milestones reached!")
    """
    goal = get_goal(goal_id)
    milestones = goal.get("milestones", [])

    # Find first unreached milestone (sorted by amount)
    for milestone in milestones:
        if not milestone.get("reached", False):
            return milestone

    return None


def get_milestone_progress(goal_id: str) -> dict[str, Any]:
    """
    Get milestone progress statistics for a goal.

    Args:
        goal_id: Goal identifier

    Returns:
        Dict with milestone progress stats:
        - total_milestones: Total number of milestones
        - reached_count: Number reached
        - remaining_count: Number remaining
        - percent_complete: Percentage of milestones reached
        - next_milestone: Next unreached milestone (or None)

    Example:
        from fin_infra.goals.milestones import get_milestone_progress

        stats = get_milestone_progress("goal_123")
        print(f"Milestones: {stats['reached_count']}/{stats['total_milestones']}")
        print(f"Progress: {stats['percent_complete']:.1f}%")
    """
    goal = get_goal(goal_id)
    milestones = goal.get("milestones", [])

    total = len(milestones)
    reached = sum(1 for m in milestones if m.get("reached", False))
    remaining = total - reached
    percent = (reached / total * 100) if total > 0 else 0

    next_milestone = get_next_milestone(goal_id)

    return {
        "total_milestones": total,
        "reached_count": reached,
        "remaining_count": remaining,
        "percent_complete": percent,
        "next_milestone": next_milestone,
    }


# ============================================================================
# Webhook Integration (Integration with svc-infra)
# ============================================================================


async def trigger_milestone_notification(
    goal_id: str,
    milestone: dict[str, Any],
    user_id: str,
) -> None:
    """
    Trigger webhook notification when milestone reached.

    Integrates with svc-infra webhooks to send notifications via:
    - Email
    - Push notifications
    - SMS
    - Slack/Discord webhooks

    Args:
        goal_id: Goal identifier
        milestone: Milestone dict that was reached
        user_id: User identifier for notification routing

    Example:
        from fin_infra.goals.milestones import trigger_milestone_notification

        await trigger_milestone_notification(
            goal_id="goal_123",
            milestone=milestone,
            user_id="user_456"
        )

    Note:
        Applications should configure webhook endpoints in svc-infra:

        from svc_infra.webhooks import add_webhooks

        add_webhooks(
            app,
            endpoints={
                "goal.milestone_reached": "https://api.app.com/webhooks/milestone"
            }
        )
    """
    try:
        # Optional: Import svc-infra webhooks if available
        from svc_infra.webhooks import trigger_webhook

        message = get_celebration_message(milestone)

        await trigger_webhook(
            event="goal.milestone_reached",
            data={
                "goal_id": goal_id,
                "user_id": user_id,
                "milestone": milestone,
                "message": message,
                "timestamp": datetime.utcnow().isoformat(),
            },
        )
    except ImportError:
        # svc-infra not available, log message instead
        message = get_celebration_message(milestone)
        print(f"[Milestone Notification] {message}")
