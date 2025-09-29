"""
Example usage of the GitHub Project Scorer
"""
import asyncio
from pathlib import Path
from main import GitHubProjectScorer


async def test_scorer():
    """Test the scorer with a simple repository"""
    
    # Example repository URL (you can change this)
    repo_url = "https://github.com/pydantic/pydantic-ai"
    
    # Initialize scorer
    scorer = GitHubProjectScorer(
        model_provider="openai",
        model_name="gpt-4o-mini"
    )
    
    try:
        # Run evaluation
        evaluation = await scorer.evaluate_repository(
            repo_url=repo_url,
            criteria_path=Path("criteria.yaml"),
            output_dir=Path("./reports"),
            cleanup=True
        )
        
        print(f"\n✅ Evaluation completed!")
        print(f"Final score: {evaluation.total_score}/{evaluation.max_total_score}")
        print(f"Percentage: {evaluation.total_score/evaluation.max_total_score*100:.1f}%")
        
        if evaluation.improvements:
            print(f"\n📋 Found {len(evaluation.improvements)} improvement suggestions")
        
    except Exception as e:
        print(f"❌ Error during evaluation: {e}")
        print("\nTip: Make sure you have set your API key:")
        print("export OPENAI_API_KEY='your-key-here'")
        print("or")
        print("export ANTHROPIC_API_KEY='your-key-here'")


if __name__ == "__main__":
    print("🚀 Testing GitHub Project Scorer")
    asyncio.run(test_scorer())