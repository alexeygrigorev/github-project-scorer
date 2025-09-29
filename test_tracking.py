"""
Test the progress and cost tracking features
"""
import asyncio
from pathlib import Path
from usage_tracker import UsageTracker, ProgressTracker


def test_progress_tracker():
    """Test progress tracking functionality"""
    print("Testing Progress Tracker...")
    
    tracker = ProgressTracker()
    criteria_names = ["Problem description", "Interface", "Documentation", "Testing"]
    
    # Start tracking
    tracker.start(len(criteria_names))
    print(f"Started: {tracker.get_progress_text()}")
    
    # Simulate evaluation
    for i, name in enumerate(criteria_names):
        success = i != 2  # Simulate failure on "Documentation"
        tracker.update(name, success)
        print(f"After {name}: {tracker.get_progress_text()}")
    
    print(f"Complete: {tracker.is_complete()}")
    print()


def test_usage_tracker():
    """Test token usage and cost calculation"""
    print("Testing Usage Tracker...")
    
    tracker = UsageTracker()
    
    # Simulate some usage
    tracker.add_usage("gpt-4", 1500, 300)  # 1500 input, 300 output tokens
    tracker.add_usage("gpt-4", 2000, 500)  # Another call
    tracker.add_usage("claude-3-sonnet-20240229", 1000, 200)  # Different model
    
    # Show breakdown
    breakdown = tracker.get_cost_breakdown()
    print(f"Total tokens: {breakdown['total_input_tokens']:,} input + {breakdown['total_output_tokens']:,} output")
    print(f"Total cost: ${breakdown['total_cost']:.4f}")
    
    print("\nPer model:")
    for model, data in breakdown['models'].items():
        print(f"  {model}: ${data['total_cost']:.4f} ({data['input_tokens']:,} + {data['output_tokens']:,} tokens)")
    
    # Show formatted summary
    print("\nFormatted summary:")
    print(tracker.format_cost_summary())


def test_pricing_lookup():
    """Test pricing configuration loading"""
    print("Testing Pricing Configuration...")
    
    tracker = UsageTracker()
    
    # Test different model lookups
    test_models = [
        "gpt-4",
        "gpt-4-turbo", 
        "claude-3-sonnet-20240229",
        "unknown-model"
    ]
    
    for model in test_models:
        pricing = tracker.get_model_pricing(model)
        print(f"{model}: ${pricing['input']:.2f}/${pricing['output']:.2f} per 1M tokens")


if __name__ == "__main__":
    test_progress_tracker()
    test_usage_tracker()
    test_pricing_lookup()