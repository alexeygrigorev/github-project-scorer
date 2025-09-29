"""
Simple test to evaluate a single criteria against the cloned repository
"""
import asyncio
from pathlib import Path
from dotenv import load_dotenv

from models import load_criteria_from_yaml
from file_analyzer import FileAnalyzer
from evaluator import ProjectEvaluator, AnalysisContext

# Load environment variables
load_dotenv()

async def test_single_criteria():
    """Test evaluating a single criteria"""
    
    # Repository path (already cloned)
    repo_path = Path("tmp/Recipes_Assistant")
    
    if not repo_path.exists():
        print("Repository not found. Please run: git clone https://github.com/lvsuno/Recipes_Assistant.git tmp/Recipes_Assistant")
        return
    
    print(f"Testing evaluation on: {repo_path}")
    
    # Load criteria
    criteria_list = load_criteria_from_yaml(Path("criteria.yaml"))
    print(f"Loaded {len(criteria_list)} criteria")
    
    # Pick the first criteria to test
    test_criteria = criteria_list[0]  # "Problem description"
    print(f"Testing criteria: {test_criteria.name}")
    
    # Setup file analyzer
    file_analyzer = FileAnalyzer(repo_path)
    
    # Gather analysis context
    project_files = file_analyzer.list_files(max_files=100)  # Limit for testing
    config_files = file_analyzer.find_config_files()
    file_stats = file_analyzer.get_file_stats()
    
    # Read README
    readme_content = ""
    readme_files = file_analyzer.find_files_by_name("readme*")
    if readme_files:
        readme_content = file_analyzer.read_file(readme_files[0], max_lines=50)
        print(f"Found README with {len(readme_content)} characters")
    
    context = AnalysisContext(
        repo_path=repo_path,
        file_analyzer=file_analyzer,
        project_files=project_files,
        config_files=config_files,
        file_stats=file_stats,
        readme_content=readme_content
    )
    
    print(f"Context: {len(project_files)} files, {len(config_files)} config files")
    print(f"File types: {file_stats}")
    
    # Initialize evaluator with OpenAI GPT-4o-mini
    evaluator = ProjectEvaluator("openai:gpt-4o-mini", file_analyzer)
    
    # Evaluate single criteria
    print(f"\nEvaluating '{test_criteria.name}'...")
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


async def test_with_tool_calls():
    """Test with tool call display"""
    
    # Repository path (already cloned)
    repo_path = Path("tmp/Recipes_Assistant")
    
    if not repo_path.exists():
        print("Repository not found. Please run: git clone https://github.com/lvsuno/Recipes_Assistant.git tmp/Recipes_Assistant")
        return
    
    print(f"Testing evaluation with tool calls on: {repo_path}")
    
    # Load criteria and pick one
    criteria_list = load_criteria_from_yaml(Path("criteria.yaml"))
    test_criteria = criteria_list[0]  # "Problem description"
    print(f"Testing criteria: {test_criteria.name}")
    
    # Setup context (minimal for testing)
    file_analyzer = FileAnalyzer(repo_path)
    project_files = file_analyzer.list_files(max_files=20)
    config_files = file_analyzer.find_config_files()
    file_stats = file_analyzer.get_file_stats()
    
    readme_content = ""
    readme_files = file_analyzer.find_files_by_name("readme*")
    if readme_files:
        readme_content = file_analyzer.read_file(readme_files[0], max_lines=30)
    
    context = AnalysisContext(
        repo_path=repo_path,
        file_analyzer=file_analyzer,
        project_files=project_files,
        config_files=config_files,
        file_stats=file_stats,
        readme_content=readme_content
    )
    
    # Create evaluator and get the agent
    evaluator = ProjectEvaluator("openai:gpt-4o-mini", file_analyzer)
    agent = evaluator.scored_agent
    
    # Create prompt
    prompt = evaluator._create_scored_prompt(test_criteria, context)
    
    print(f"\nRunning agent with tool call tracking...")
    
    # Run with message tracking
    result = await agent.run(prompt)
    
    # Display tool calls
    messages = result.new_messages()
    tool_calls = {}
    
    print(f"\nMessage History ({len(messages)} messages):")
    for i, message in enumerate(messages):
        print(f"\nMessage {i+1}: {type(message).__name__}")
        
        for j, part in enumerate(message.parts):
            kind = part.part_kind
            print(f"  Part {j+1}: {kind}")
            
            if kind == "text":
                content = part.content[:200] + "..." if len(part.content) > 200 else part.content
                print(f"    Content: {content}")
            
            elif kind == "tool-call":
                call_id = part.tool_call_id
                tool_calls[call_id] = part
                print(f"    Tool: {part.tool_name}")
                print(f"    Args: {part.args}")
                print(f"    Call ID: {call_id}")
            
            elif kind == "tool-return":
                call_id = part.tool_call_id
                if call_id in tool_calls:
                    call = tool_calls[call_id]
                    print(f"    Tool: {call.tool_name}")
                    print(f"    Result: {part.content[:200]}...")
    
    print(f"\nFinal Result:")
    print(f"  Score: {result.output.score}")
    print(f"  Reasoning: {result.output.reasoning[:200]}...")
    
    # Show usage
    if result.usage():
        usage = result.usage()
        cost = (usage.input_tokens * 0.15 + usage.output_tokens * 0.6) / 1_000_000
        print(f"  Usage: {usage.input_tokens} input + {usage.output_tokens} output tokens")
        print(f"  Cost: ${cost:.6f}")


if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == "tools":
        asyncio.run(test_with_tool_calls())
    else:
        asyncio.run(test_single_criteria())