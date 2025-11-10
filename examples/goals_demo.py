#!/usr/bin/env python3
"""
Goal Management Demo

Demonstrates comprehensive goal tracking with milestones and funding allocation.

Usage:
    poetry run python examples/goals_demo.py

Note:
    This demo uses the direct function API from fin_infra.goals.management.
    For FastAPI integration, use add_goals(app) which provides REST endpoints.
    See src/fin_infra/docs/goals.md for full documentation.
"""

from datetime import datetime, timedelta

from fin_infra.goals import (
    create_goal,
    update_goal,
    list_goals,
    get_goal,
    get_goal_progress,
    add_milestone,
    check_milestones,
    get_milestone_progress,
    link_account_to_goal,
    get_goal_funding_sources,
)


def main():
    """Run goals demo scenarios."""
    print("=" * 80)
    print("Goal Management Demo")
    print("=" * 80)
    print("Demonstrates: CRUD, milestones, funding allocation, and progress tracking")
    print("=" * 80)

    # ========================================================================
    # Scenario 1: Emergency Fund with Milestones
    # ========================================================================
    print("\n" + "=" * 80)
    print("Scenario 1: Emergency Fund with Milestones")
    print("=" * 80)

    # Create emergency fund goal (6 months expenses = $18,000)
    emergency_fund = create_goal(
        user_id="demo_user",
        name="6-Month Emergency Fund",
        goal_type="savings",  # Use string, not enum
        target_amount=18000.00,
        current_amount=0.00,
        deadline=datetime.now() + timedelta(days=730),  # 2 years
        description="Save 6 months of expenses ($3,000/month)",
    )

    print(f"\n✅ Created Goal: {emergency_fund['name']}")
    print(f"   Target: ${emergency_fund['target_amount']:,.2f}")
    print(f"   Deadline: {emergency_fund['deadline'].strftime('%Y-%m-%d')}")

    # Add milestones at each month (1-6 months)
    print("\n📍 Adding Milestones:")
    for month in range(1, 7):
        milestone = add_milestone(
            goal_id=emergency_fund["id"],
            amount=month * 3000.00,
            description=f"{month} month{'s' if month > 1 else ''} of expenses saved",
            target_date=datetime.now() + timedelta(days=month * 60),
        )
        print(f"   ${milestone['amount']:,.2f} - {milestone['description']}")

    # Simulate monthly savings
    print("\n💰 Monthly Savings Progress:")
    for month in range(1, 7):
        current = month * 500.00  # Save $500/month
        emergency_fund = update_goal(
            goal_id=emergency_fund["id"],
            current_amount=current,
        )

        # Check milestones
        newly_reached = check_milestones(goal_id=emergency_fund["id"])

        # Get progress
        progress = get_goal_progress(goal_id=emergency_fund["id"])

        print(f"   Month {month}: ${current:,.2f} ({progress['percent_complete']:.1f}%)", end="")
        if newly_reached:
            print(f" 🎉 Milestone reached!")
        else:
            print()

    # Get milestone progress
    milestone_progress = get_milestone_progress(goal_id=emergency_fund["id"])
    print(f"\n📊 Milestone Progress:")
    print(f"   Reached: {milestone_progress['reached_count']}/{milestone_progress['total_milestones']}")
    print(f"   Completion: {milestone_progress['percent_complete']:.1f}%")
    if milestone_progress.get("next_milestone"):
        next_m = milestone_progress["next_milestone"]
        print(f"   Next: ${next_m['amount']:,.2f} - {next_m['description']}")

    # ========================================================================
    # Scenario 2: Multi-Goal Funding Allocation
    # ========================================================================
    print("\n" + "=" * 80)
    print("Scenario 2: Multi-Goal Funding Allocation")
    print("=" * 80)

    # Create 3 goals
    vacation = create_goal(
        user_id="demo_user",
        name="Hawaii Vacation",
        goal_type="savings",
        target_amount=5000.00,
        current_amount=0.00,
        deadline=datetime.now() + timedelta(days=180),
        description="Summer vacation to Hawaii",
    )

    down_payment = create_goal(
        user_id="demo_user",
        name="House Down Payment",
        goal_type="savings",
        target_amount=50000.00,
        current_amount=10000.00,
        deadline=datetime.now() + timedelta(days=1095),  # 3 years
        description="20% down payment on $250k house",
    )

    print(f"\n✅ Created Goals:")
    print(f"   1. {emergency_fund['name']} (${emergency_fund['target_amount']:,.2f})")
    print(f"   2. {vacation['name']} (${vacation['target_amount']:,.2f})")
    print(f"   3. {down_payment['name']} (${down_payment['target_amount']:,.2f})")

    # Allocate funding sources
    print("\n💵 Funding Allocation:")

    # Emergency Fund: 100% from high-yield savings
    link_account_to_goal(
        goal_id=emergency_fund["id"],
        account_id="savings_hysa",
        account_name="High Yield Savings",
        allocation_percent=100.0,
    )
    print(f"   {emergency_fund['name']}:")
    print(f"     • High Yield Savings: 100%")

    # Vacation: 60% checking + 40% savings
    link_account_to_goal(
        goal_id=vacation["id"],
        account_id="checking_001",
        account_name="Primary Checking",
        allocation_percent=60.0,
    )
    link_account_to_goal(
        goal_id=vacation["id"],
        account_id="savings_hysa",
        account_name="High Yield Savings",
        allocation_percent=40.0,
    )
    print(f"   {vacation['name']}:")
    print(f"     • Primary Checking: 60%")
    print(f"     • High Yield Savings: 40%")

    # Down Payment: 50% savings + 30% investment + 20% checking
    link_account_to_goal(
        goal_id=down_payment["id"],
        account_id="savings_hysa",
        account_name="High Yield Savings",
        allocation_percent=50.0,
    )
    link_account_to_goal(
        goal_id=down_payment["id"],
        account_id="investment_brokerage",
        account_name="Brokerage Account",
        allocation_percent=30.0,
    )
    link_account_to_goal(
        goal_id=down_payment["id"],
        account_id="checking_001",
        account_name="Primary Checking",
        allocation_percent=20.0,
    )
    print(f"   {down_payment['name']}:")
    print(f"     • High Yield Savings: 50%")
    print(f"     • Brokerage Account: 30%")
    print(f"     • Primary Checking: 20%")

    # View funding details
    print("\n📋 Funding Summary:")
    for goal_obj in [emergency_fund, vacation, down_payment]:
        funding = get_goal_funding_sources(goal_id=goal_obj["id"])
        print(f"   {goal_obj['name']}:")
        for source in funding:
            print(f"     • {source['account_name']}: {source['allocation_percent']:.0f}%")

    # ========================================================================
    # Scenario 3: Debt Payoff Goal
    # ========================================================================
    print("\n" + "=" * 80)
    print("Scenario 3: Credit Card Debt Payoff")
    print("=" * 80)

    # Create debt payoff goal (starts at full debt, decreases to $0)
    debt_goal = create_goal(
        user_id="demo_user",
        name="Credit Card Payoff",
        goal_type="debt",
        target_amount=0.00,  # Goal: $0 debt
        current_amount=8500.00,  # Start at $8,500 debt
        deadline=datetime.now() + timedelta(days=365),
        description="Pay off Chase Sapphire balance (22% APR)",
        # status defaults to "active",
    )

    print(f"\n✅ Created Debt Goal: {debt_goal['name']}")
    print(f"   Starting Debt: ${debt_goal['current_amount']:,.2f}")
    print(f"   Target: $0.00 (debt-free)")
    print(f"   Deadline: {debt_goal['deadline'].strftime('%Y-%m-%d')}")

    # Add payoff milestones (decreasing amounts)
    print("\n📍 Payoff Milestones:")
    milestones = [6000.00, 4000.00, 2000.00, 0.00]
    for amount in milestones:
        milestone = add_milestone(
            goal_id=debt_goal["id"],
            amount=amount,
            description=f"Debt reduced to ${amount:,.2f}",
        )
        print(f"   ${milestone['amount']:,.2f} - {milestone['description']}")

    # Simulate monthly payments
    print("\n💳 Monthly Payment Progress:")
    monthly_payment = 750.00
    for month in range(1, 13):
        current_debt = max(0, debt_goal["current_amount"] - (month * monthly_payment))
        debt_goal = update_goal(
            goal_id=debt_goal["id"],
            current_amount=current_debt,
        )

        # Check milestones (debt decreasing)
        newly_reached = check_milestones(goal_id=debt_goal["id"])

        print(f"   Month {month}: ${current_debt:,.2f} remaining", end="")
        if newly_reached:
            print(f" 🎉 Milestone!")
        else:
            print()

        # Check if paid off
        if current_debt == 0:
            update_goal(
                goal_id=debt_goal["id"],
                status="completed",
            )
            print(f"\n🎊 DEBT PAID OFF! Completed in {month} months!")
            break

    # ========================================================================
    # Scenario 4: Goal Lifecycle Management
    # ========================================================================
    print("\n" + "=" * 80)
    print("Scenario 4: Goal Lifecycle Management")
    print("=" * 80)

    # Create a short-term goal
    short_term = create_goal(
        user_id="demo_user",
        name="New Laptop",
        goal_type="savings",
        target_amount=2000.00,
        current_amount=0.00,
        deadline=datetime.now() + timedelta(days=90),
        description="MacBook Pro for work",
        # status defaults to "active",
    )

    print(f"\n✅ Created Goal: {short_term['name']}")
    print(f"   Status: {short_term['status']}")

    # Pause goal temporarily
    short_term = update_goal(
        goal_id=short_term["id"],
        status="paused",
    )
    print(f"\n⏸️  Paused Goal: {short_term['name']}")
    print(f"   Status: {short_term['status']}")

    # Resume goal
    short_term = update_goal(
        goal_id=short_term["id"],
        # status defaults to "active",
    )
    print(f"\n▶️  Resumed Goal: {short_term['name']}")
    print(f"   Status: {short_term['status']}")

    # Reach target and complete
    short_term = update_goal(
        goal_id=short_term["id"],
        current_amount=2000.00,
        status="completed",
    )
    print(f"\n🎯 Completed Goal: {short_term['name']}")
    print(f"   Current: ${short_term['current_amount']:,.2f}")
    print(f"   Target: ${short_term['target_amount']:,.2f}")
    print(f"   Status: {short_term['status']}")

    # ========================================================================
    # Summary
    # ========================================================================
    print("\n" + "=" * 80)
    print("Summary")
    print("=" * 80)

    # List all goals
    all_goals = list_goals(user_id="demo_user")

    print(f"\n📊 Total Goals: {len(all_goals)}")
    active = [g for g in all_goals if g["status"] == "active"]
    completed = [g for g in all_goals if g["status"] == "completed"]
    print(f"   Active: {len(active)}")
    print(f"   Completed: {len(completed)}")

    print("\n💰 Active Goals Progress:")
    for goal in active:
        progress = get_goal_progress(goal_id=goal["id"])
        print(
            f"   {goal['name']}: "
            f"${goal['current_amount']:,.2f} / ${goal['target_amount']:,.2f} "
            f"({progress['percent_complete']:.1f}%)"
        )

    print("\n✨ Demo completed successfully!")
    print("=" * 80)


if __name__ == "__main__":
    main()
