"""
Simple test for enhanced evaluation with notebooks
"""
import asyncio
from pathlib import Path
from dotenv import load_dotenv

from models import load_criteria_from_yaml
from file_analyzer import FileAnalyzer
from evaluator import ProjectEvaluator, AnalysisContext

# Load environment variables
load_dotenv()

async def test_enhanced_evaluation():
    """Test enhanced evaluation with notebooks and relative paths"""
    
    # Repository path (already cloned)
    repo_path = Path("tmp/Recipes_Assistant")
    
    if not repo_path.exists():
        print("Repository not found. Please run: git clone https://github.com/lvsuno/Recipes_Assistant.git tmp/Recipes_Assistant")
        return
    
    print(f"Testing enhanced evaluation on: {repo_path}")
    
    # Load criteria - test just the first one
    criteria_list = load_criteria_from_yaml(Path("criteria.yaml"))
    test_criteria = criteria_list[0]  # "Problem description"
    print(f"Testing criteria: {test_criteria.name}")
    
    # Setup file analyzer and evaluator
    file_analyzer = FileAnalyzer(repo_path)
    evaluator = ProjectEvaluator("openai:gpt-4o-mini", file_analyzer)
    
    # Create minimal context
    context = AnalysisContext(
        repo_path=repo_path,
        file_analyzer=file_analyzer,
        project_files=[],  # Not used anymore since agents use tools
        config_files={},   # Not used anymore
        file_stats={},     # Not used anymore  
        readme_content=""  # Not used anymore
    )
    
    print(f"\nEvaluating '{test_criteria.name}' with enhanced system...")
    try:
        result = await evaluator.evaluate_criteria(test_criteria, context)
        
        print(f"\nResult:")
        print(f"  Score: {result.score}/{result.max_score}")
        print(f"  Reasoning: {result.reasoning}")
        print(f"  Evidence: {result.evidence}")
        
        # Show usage
        usage_summary = evaluator.usage_tracker.format_cost_summary()
        print(usage_summary)
        
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_enhanced_evaluation())