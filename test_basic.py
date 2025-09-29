"""
Quick test for notebook formatting and relative paths
"""
from pathlib import Path
from file_analyzer import FileAnalyzer

def test_basic_functionality():
    """Test basic FileAnalyzer functionality"""
    
    # Repository path (already cloned)
    repo_path = Path("tmp/Recipes_Assistant")
    
    if not repo_path.exists():
        print("Repository not found. Please run: git clone https://github.com/lvsuno/Recipes_Assistant.git tmp/Recipes_Assistant")
        return
    
    print(f"Testing functionality on: {repo_path}")
    
    # Setup file analyzer
    file_analyzer = FileAnalyzer(repo_path)
    
    # Test basic methods
    print("\n1. Testing list_files()...")
    files = file_analyzer.list_files(max_files=10)
    print(f"Found {len(files)} files (showing first 10):")
    for f in files[:5]:
        print(f"  - {f}")
    
    print("\n2. Testing find_files_by_name() for notebooks...")
    notebooks = file_analyzer.find_files_by_name("*.ipynb")
    print(f"Found {len(notebooks)} notebook files:")
    for nb in notebooks:
        print(f"  - {nb}")
    
    if notebooks:
        print(f"\n3. Testing read_file() on notebook: {notebooks[0]}")
        try:
            content = file_analyzer.read_file(notebooks[0], max_lines=20)
            print(f"Notebook content (first 500 chars):")
            print(content[:500] + "..." if len(content) > 500 else content)
        except Exception as e:
            print(f"Error reading notebook: {e}")
    
    print("\n4. Testing get_file_stats()...")
    stats = file_analyzer.get_file_stats()
    print(f"File statistics: {stats}")
    
    print("\nBasic functionality test completed!")

if __name__ == "__main__":
    test_basic_functionality()