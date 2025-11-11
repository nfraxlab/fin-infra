#!/usr/bin/env python3
"""Goals demo - see docs/goals.md for details."""
from datetime import datetime, timedelta
from fin_infra.goals import create_goal, update_goal, add_milestone, check_milestones, get_goal_progress

def main():
    print("Goal Management Demo")
    goal = create_goal(user_id="demo", name="Emergency Fund", goal_type="savings", 
                       target_amount=10000.00, deadline=datetime.now() + timedelta(days=365))
    print(f"Created: {goal['name']} (${goal['target_amount']:,.2f})")
    
    add_milestone(goal_id=goal["id"], amount=2500.00, description="25%")
    add_milestone(goal_id=goal["id"], amount=5000.00, description="50%")
    print("Added milestones")
    
    for month in [1, 2, 3, 4, 5]:
        goal = update_goal(goal_id=goal["id"], updates={"current_amount": month * 1000.00})
        check_milestones(goal_id=goal["id"])
        progress = get_goal_progress(goal_id=goal["id"])
        print(f"Month {month}: ${month * 1000:,.2f} ({progress['percent_complete']:.0f}%)")
    
    print("✅ Demo complete! See docs/goals.md for full documentation.")

if __name__ == "__main__":
    main()
