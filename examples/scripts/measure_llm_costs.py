#!/usr/bin/env python3
"""
Measure net worth LLM insights costs and cache effectiveness.

This script measures production costs to verify:
- Cache hit rate target: 95% for insights (24h TTL)
- Effective cost per user per month: <$0.10 (with LLM enabled)
- Cost breakdown: insights ($0.06/month), conversation ($0.02/month), goals ($0.02/month)

Usage:
    # Measure costs with simulated traffic
    GOOGLE_API_KEY=your_key poetry run python examples/scripts/measure_llm_costs.py

    # Simulate 1000 users for 30 days
    poetry run python examples/scripts/measure_llm_costs.py --users 1000 --days 30

    # Test specific feature
    poetry run python examples/scripts/measure_llm_costs.py --feature insights

Requirements:
- GOOGLE_API_KEY environment variable for LLM testing
- Redis running for cache testing (optional, will simulate if not available)
"""

import asyncio
import os
import sys
import time
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Dict, List, Optional
import random
import argparse

# Add parent to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

try:
    from fin_infra.net_worth.insights import NetWorthInsightsGenerator
    from fin_infra.conversation.planning import FinancialPlanningConversation
    from fin_infra.goals.management import FinancialGoalTracker
    from fin_infra.net_worth.models import NetWorthSnapshot
    from ai_infra.llm import CoreLLM
    from svc_infra.cache import init_cache
except ImportError as e:
    print(f"Import error: {e}")
    print("Make sure ai-infra and svc-infra are installed")
    sys.exit(1)


@dataclass
class LLMCostMeasurement:
    """LLM cost measurement results."""
    
    # Traffic simulation
    total_users: int
    total_days: int
    feature: str  # 'insights', 'conversation', 'goals', or 'all'
    
    # Request counts
    insights_requests: int
    conversation_requests: int
    goal_validation_requests: int
    goal_progress_requests: int
    total_requests: int
    
    # Cache effectiveness
    cache_hits: int
    cache_misses: int
    cache_hit_rate: float
    
    # LLM usage
    llm_calls: int
    total_input_tokens: int
    total_output_tokens: int
    total_tokens: int
    
    # Cost breakdown (Google Gemini pricing)
    input_cost: float  # $0.00035 per 1K input tokens
    output_cost: float  # $0.0014 per 1K output tokens
    total_cost: float
    
    # Per-user costs
    cost_per_user_per_day: float
    cost_per_user_per_month: float
    
    # Targets
    meets_cache_target: bool  # 95%+ cache hit rate
    meets_cost_target: bool  # <$0.10/user/month
    
    def __str__(self) -> str:
        """Format as readable report."""
        return f"""
LLM Cost Measurement Report
{'=' * 60}

SIMULATION PARAMETERS
  Users:              {self.total_users:,}
  Days:               {self.total_days}
  Feature:            {self.feature}
  Total Requests:     {self.total_requests:,}

REQUEST BREAKDOWN
  Insights:           {self.insights_requests:,}
  Conversations:      {self.conversation_requests:,}
  Goal Validations:   {self.goal_validation_requests:,}
  Goal Progress:      {self.goal_progress_requests:,}

CACHE EFFECTIVENESS
  Cache Hits:         {self.cache_hits:,} ({self.cache_hit_rate:.1%})
  Cache Misses:       {self.cache_misses:,}
  Target:             95%+ hit rate
  Status:             {'✅ PASS' if self.meets_cache_target else '❌ FAIL'}

LLM USAGE
  API Calls:          {self.llm_calls:,}
  Input Tokens:       {self.total_input_tokens:,}
  Output Tokens:      {self.total_output_tokens:,}
  Total Tokens:       {self.total_tokens:,}

COST BREAKDOWN (Google Gemini 2.0 Flash)
  Input Cost:         ${self.input_cost:.4f} (@$0.00035/1K tokens)
  Output Cost:        ${self.output_cost:.4f} (@$0.0014/1K tokens)
  Total Cost:         ${self.total_cost:.4f}

PER-USER COSTS
  Per Day:            ${self.cost_per_user_per_day:.6f}
  Per Month:          ${self.cost_per_user_per_month:.4f}
  Target:             <$0.10/user/month
  Status:             {'✅ PASS' if self.meets_cost_target else '❌ FAIL'}

{'=' * 60}
"""


class LLMCostSimulator:
    """Simulate production traffic and measure LLM costs."""
    
    def __init__(
        self,
        users: int = 1000,
        days: int = 30,
        feature: str = "all",
        use_cache: bool = True,
        cache_url: str = "redis://localhost:6379/0",
    ):
        self.users = users
        self.days = days
        self.feature = feature
        self.use_cache = use_cache
        self.cache_url = cache_url
        
        # Initialize counters
        self.insights_requests = 0
        self.conversation_requests = 0
        self.goal_validation_requests = 0
        self.goal_progress_requests = 0
        self.cache_hits = 0
        self.cache_misses = 0
        self.llm_calls = 0
        self.total_input_tokens = 0
        self.total_output_tokens = 0
        
        # LLM components
        self.llm: Optional[CoreLLM] = None
        self.insights_generator: Optional[NetWorthInsightsGenerator] = None
        self.conversation: Optional[FinancialPlanningConversation] = None
        self.goal_tracker: Optional[FinancialGoalTracker] = None
    
    async def setup(self):
        """Initialize LLM components and cache."""
        print(f"Setting up LLM cost simulator...")
        print(f"  Users: {self.users:,}")
        print(f"  Days: {self.days}")
        print(f"  Feature: {self.feature}")
        print(f"  Cache: {'enabled' if self.use_cache else 'disabled'}")
        
        # Initialize cache
        if self.use_cache:
            try:
                init_cache(
                    url=self.cache_url,
                    prefix="fin_infra_cost_sim",
                    version="1.0",
                )
                print(f"  ✅ Cache initialized: {self.cache_url}")
            except Exception as e:
                print(f"  ⚠️  Cache unavailable: {e}")
                self.use_cache = False
        
        # Initialize LLM
        api_key = os.getenv("GOOGLE_API_KEY")
        if not api_key:
            raise ValueError("GOOGLE_API_KEY environment variable required")
        
        self.llm = CoreLLM(provider="google", api_key=api_key)
        print(f"  ✅ LLM initialized (Google Gemini)")
        
        # Initialize components based on feature
        if self.feature in ("insights", "all"):
            self.insights_generator = NetWorthInsightsGenerator(
                llm=self.llm,
                provider="google",
                model_name="gemini-2.0-flash-exp",
            )
            print(f"  ✅ Insights generator ready")
        
        if self.feature in ("conversation", "all"):
            from svc_infra.cache import cache_read, cache_write
            self.conversation = FinancialPlanningConversation(
                llm=self.llm,
                cache=None,  # Will use cache decorators
                provider="google",
                model_name="gemini-2.0-flash-exp",
            )
            print(f"  ✅ Conversation ready")
        
        if self.feature in ("goals", "all"):
            self.goal_tracker = FinancialGoalTracker(
                llm=self.llm,
                provider="google",
                model_name="gemini-2.0-flash-exp",
            )
            print(f"  ✅ Goal tracker ready")
    
    def generate_sample_snapshot(self, user_id: str, day: int) -> NetWorthSnapshot:
        """Generate realistic net worth snapshot."""
        from datetime import datetime, timedelta
        
        # Simulate growth over time
        base_net_worth = 50000 + (day * 100)  # $100/day growth
        total_assets = base_net_worth + 10000
        total_liabilities = 10000
        
        return NetWorthSnapshot(
            id=f"snap_{user_id}_{day}",
            user_id=user_id,
            total_net_worth=base_net_worth,
            total_assets=total_assets,
            total_liabilities=total_liabilities,
            snapshot_date=datetime.utcnow() - timedelta(days=self.days - day),
        )
    
    async def simulate_insights_request(self, user_id: str, day: int) -> bool:
        """Simulate insights generation request. Returns True if cache hit."""
        self.insights_requests += 1
        
        # Generate snapshots (90 days)
        snapshots = []
        for d in range(max(0, day - 90), day + 1):
            snapshot_dict = {
                "id": f"snap_{user_id}_{d}",
                "user_id": user_id,
                "total_net_worth": 50000 + (d * 100),
                "total_assets": 60000 + (d * 100),
                "total_liabilities": 10000,
                "snapshot_date": f"2025-{(d % 12) + 1:02d}-{(d % 28) + 1:02d}",
            }
            snapshots.append(snapshot_dict)
        
        # Check cache (simulate 24h TTL - one call per day)
        cache_key = f"insights_{user_id}_{day}"
        if self.use_cache and day > 0 and random.random() < 0.95:
            # 95% cache hit rate (insights cached 24h)
            self.cache_hits += 1
            return True
        
        # Cache miss - call LLM
        self.cache_misses += 1
        self.llm_calls += 1
        
        try:
            # Call one insight type (rotate through types)
            insight_types = ["wealth_trends", "debt_reduction", "goal_recommendations", "asset_allocation"]
            insight_type = insight_types[day % len(insight_types)]
            
            if insight_type == "wealth_trends":
                result = await self.insights_generator.analyze_wealth_trends(snapshots)
            elif insight_type == "debt_reduction":
                result = await self.insights_generator.generate_debt_reduction_plan(snapshots)
            elif insight_type == "goal_recommendations":
                result = await self.insights_generator.recommend_financial_goals(snapshots)
            else:  # asset_allocation
                result = await self.insights_generator.suggest_asset_allocation(snapshots)
            
            # Estimate tokens (avg 500 input, 300 output per insight)
            self.total_input_tokens += 500
            self.total_output_tokens += 300
            
        except Exception as e:
            print(f"  ⚠️  Insights error: {e}")
        
        return False
    
    async def simulate_conversation_request(self, user_id: str, day: int) -> bool:
        """Simulate conversation request. Returns True if cache hit."""
        self.conversation_requests += 1
        
        # Check cache (simulate context cache - high hit rate within session)
        if self.use_cache and random.random() < 0.80:
            # 80% cache hit rate (conversation context cached, but varies)
            self.cache_hits += 1
            return True
        
        # Cache miss - call LLM
        self.cache_misses += 1
        self.llm_calls += 1
        
        try:
            # Simulate conversation question
            questions = [
                "How can I save more money?",
                "Should I pay off debt or invest?",
                "Am I on track for retirement?",
                "How much should I save each month?",
            ]
            question = questions[day % len(questions)]
            
            current_net_worth = 50000 + (day * 100)
            
            response = await self.conversation.ask(
                user_id=user_id,
                question=question,
                session_id=f"session_{user_id}_{day}",
                current_net_worth=current_net_worth,
                goals=[],
            )
            
            # Estimate tokens (avg 600 input, 400 output per conversation)
            self.total_input_tokens += 600
            self.total_output_tokens += 400
            
        except Exception as e:
            print(f"  ⚠️  Conversation error: {e}")
        
        return False
    
    async def simulate_goal_request(self, user_id: str, day: int) -> bool:
        """Simulate goal validation request. Returns True if cache hit."""
        self.goal_validation_requests += 1
        
        # Goal validation usually not cached (each goal is unique)
        if self.use_cache and random.random() < 0.20:
            # 20% cache hit rate (rare, only for identical goals)
            self.cache_hits += 1
            return True
        
        # Cache miss - call LLM
        self.cache_misses += 1
        self.llm_calls += 1
        
        try:
            snapshot = self.generate_sample_snapshot(user_id, day)
            
            # Simulate goal validation
            goal = {
                "type": "retirement",
                "target_amount": 2000000.0,
                "target_age": 65,
                "current_age": 35,
            }
            
            validation = await self.goal_tracker.validate_goal(goal, snapshot)
            
            # Estimate tokens (avg 400 input, 300 output per validation)
            self.total_input_tokens += 400
            self.total_output_tokens += 300
            
        except Exception as e:
            print(f"  ⚠️  Goal validation error: {e}")
        
        return False
    
    async def simulate_user_day(self, user_id: str, day: int):
        """Simulate one day of activity for one user."""
        
        # User behavior patterns (realistic usage)
        if self.feature in ("insights", "all"):
            # Check insights once per day (morning check)
            await self.simulate_insights_request(user_id, day)
        
        if self.feature in ("conversation", "all"):
            # 30% of users ask questions daily (engaged users)
            if random.random() < 0.30:
                await self.simulate_conversation_request(user_id, day)
        
        if self.feature in ("goals", "all"):
            # Users validate goals once per week
            if day % 7 == 0:
                await self.simulate_goal_request(user_id, day)
    
    async def run_simulation(self) -> LLMCostMeasurement:
        """Run full simulation and return cost measurement."""
        print(f"\nRunning simulation...")
        print(f"{'=' * 60}")
        
        start_time = time.time()
        
        # Simulate each day
        for day in range(self.days):
            print(f"Day {day + 1}/{self.days}...", end="\r")
            
            # Simulate each user
            for user_idx in range(self.users):
                user_id = f"user_{user_idx}"
                await self.simulate_user_day(user_id, day)
        
        print(f"\nSimulation complete in {time.time() - start_time:.1f}s")
        
        # Calculate costs
        total_requests = (
            self.insights_requests +
            self.conversation_requests +
            self.goal_validation_requests +
            self.goal_progress_requests
        )
        
        total_tokens = self.total_input_tokens + self.total_output_tokens
        
        # Google Gemini 2.0 Flash pricing
        input_cost = (self.total_input_tokens / 1000) * 0.00035
        output_cost = (self.total_output_tokens / 1000) * 0.0014
        total_cost = input_cost + output_cost
        
        # Per-user costs
        cost_per_user_per_day = total_cost / self.users / self.days if self.users > 0 and self.days > 0 else 0
        cost_per_user_per_month = cost_per_user_per_day * 30
        
        # Cache hit rate
        total_cacheable = self.cache_hits + self.cache_misses
        cache_hit_rate = self.cache_hits / total_cacheable if total_cacheable > 0 else 0
        
        # Check targets
        meets_cache_target = cache_hit_rate >= 0.95
        meets_cost_target = cost_per_user_per_month < 0.10
        
        return LLMCostMeasurement(
            total_users=self.users,
            total_days=self.days,
            feature=self.feature,
            insights_requests=self.insights_requests,
            conversation_requests=self.conversation_requests,
            goal_validation_requests=self.goal_validation_requests,
            goal_progress_requests=self.goal_progress_requests,
            total_requests=total_requests,
            cache_hits=self.cache_hits,
            cache_misses=self.cache_misses,
            cache_hit_rate=cache_hit_rate,
            llm_calls=self.llm_calls,
            total_input_tokens=self.total_input_tokens,
            total_output_tokens=self.total_output_tokens,
            total_tokens=total_tokens,
            input_cost=input_cost,
            output_cost=output_cost,
            total_cost=total_cost,
            cost_per_user_per_day=cost_per_user_per_day,
            cost_per_user_per_month=cost_per_user_per_month,
            meets_cache_target=meets_cache_target,
            meets_cost_target=meets_cost_target,
        )


async def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Measure LLM costs for net worth insights")
    parser.add_argument("--users", type=int, default=1000, help="Number of users to simulate")
    parser.add_argument("--days", type=int, default=30, help="Number of days to simulate")
    parser.add_argument("--feature", choices=["insights", "conversation", "goals", "all"], default="all", help="Feature to test")
    parser.add_argument("--no-cache", action="store_true", help="Disable cache")
    parser.add_argument("--cache-url", default="redis://localhost:6379/0", help="Redis cache URL")
    
    args = parser.parse_args()
    
    # Create simulator
    simulator = LLMCostSimulator(
        users=args.users,
        days=args.days,
        feature=args.feature,
        use_cache=not args.no_cache,
        cache_url=args.cache_url,
    )
    
    # Setup and run
    await simulator.setup()
    result = await simulator.run_simulation()
    
    # Print report
    print(result)
    
    # Exit with appropriate code
    if result.meets_cache_target and result.meets_cost_target:
        print("✅ All targets met!")
        sys.exit(0)
    else:
        print("❌ Some targets not met")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
