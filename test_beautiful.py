"""
Test the beautiful evaluation system on a few criteria
"""
import asyncio
from pathlib import Path
from dotenv import load_dotenv

from models import load_criteria_from_yaml
from file_analyzer import FileAnalyzer  
from evaluator import ProjectEvaluator, AnalysisContext

# Load environment variables
load_dotenv()

async def test_beautiful_evaluation():
    """Test the beautiful evaluation system"""
    
    # Repository path (already cloned)
    repo_path = Path("tmp/Recipes_Assistant")
    
    if not repo_path.exists():
        print("Repository not found. Please run: git clone https://github.com/lvsuno/Recipes_Assistant.git tmp/Recipes_Assistant")
        return
    
    print(f"Testing beautiful evaluation on: {repo_path}")
    
    # Load first 3 criteria only for quick test
    criteria_list = load_criteria_from_yaml(Path("criteria.yaml"))[:3]
    print(f"Testing {len(criteria_list)} criteria")
    
    # Setup file analyzer and evaluator
    file_analyzer = FileAnalyzer(repo_path)
    evaluator = ProjectEvaluator("openai:gpt-4o-mini", file_analyzer)
    
    # Create minimal context
    context = AnalysisContext(
        repo_path=repo_path,
        file_analyzer=file_analyzer,
        project_files=[],
        config_files={},
        file_stats={},
        readme_content=""
    )
    
    print(f"\nStarting beautiful evaluation...")
    try:
        results = await evaluator.evaluate_project(criteria_list, context)
        
        print(f"\nResults summary:")
        for result in results:
            print(f"  {result.criteria_name}: {result.score}/{result.max_score}")
        
        # Show usage
        usage_summary = evaluator.usage_tracker.format_cost_summary()
        print(f"\n{usage_summary}")
        
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_beautiful_evaluation())