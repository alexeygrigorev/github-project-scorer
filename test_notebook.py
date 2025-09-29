"""
Test notebook-specific evaluation
"""
import asyncio
from pathlib import Path
from dotenv import load_dotenv

from models import load_criteria_from_yaml
from file_analyzer import FileAnalyzer
from evaluator import ProjectEvaluator, AnalysisContext

# Load environment variables
load_dotenv()

async def test_notebook_evaluation():
    """Test evaluation that involves notebooks"""
    
    # Repository path (already cloned)
    repo_path = Path("tmp/Recipes_Assistant")
    
    if not repo_path.exists():
        print("Repository not found. Please run: git clone https://github.com/lvsuno/Recipes_Assistant.git tmp/Recipes_Assistant")
        return
    
    print(f"Testing notebook evaluation on: {repo_path}")
    
    # Load criteria - pick one that might involve notebooks (data quality)
    criteria_list = load_criteria_from_yaml(Path("criteria.yaml"))
    
    # Find a criteria that would benefit from notebook analysis
    test_criteria = None
    for criteria in criteria_list:
        if "data" in criteria.name.lower() or "quality" in criteria.name.lower():
            test_criteria = criteria
            break
    
    if not test_criteria:
        test_criteria = criteria_list[3]  # Pick a different one
    
    print(f"Testing criteria: {test_criteria.name}")
    
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
    
    print(f"\nEvaluating '{test_criteria.name}' (should examine notebooks)...")
    try:
        result = await evaluator.evaluate_criteria(test_criteria, context)
        
        print(f"\nResult:")
        print(f"  Score: {result.score}/{result.max_score}")
        print(f"  Reasoning: {result.reasoning[:200]}...")
        print(f"  Evidence: {result.evidence}")
        
        # Show usage
        usage_summary = evaluator.usage_tracker.format_cost_summary()
        print(usage_summary)
        
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_notebook_evaluation())