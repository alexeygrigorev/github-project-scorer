"""
Test script to verify explicit criteria typing
"""
from pathlib import Path
from models import load_criteria_from_yaml, ScoredCriteria, ChecklistCriteria


def test_explicit_typing():
    """Test that criteria are loaded with explicit types"""
    
    print("🧪 Testing explicit criteria typing...")
    
    # Load criteria
    criteria_path = Path("criteria.yaml")
    criteria_list = load_criteria_from_yaml(criteria_path)
    
    print(f"✅ Loaded {len(criteria_list)} criteria")
    
    # Check types
    scored_count = 0
    checklist_count = 0
    
    for criteria in criteria_list:
        if isinstance(criteria, ScoredCriteria):
            scored_count += 1
            print(f"📊 Scored: {criteria.name} (max score: {criteria.max_score})")
            
        elif isinstance(criteria, ChecklistCriteria):
            checklist_count += 1
            print(f"✅ Checklist: {criteria.name} (max score: {criteria.max_score})")
            print(f"   Items: {[item.description for item in criteria.items]}")
            
        else:
            print(f"❌ Unknown type: {criteria.name} - {type(criteria)}")
    
    print(f"\n📈 Summary:")
    print(f"   - Scored criteria: {scored_count}")
    print(f"   - Checklist criteria: {checklist_count}")
    print(f"   - Total: {len(criteria_list)}")
    
    # Verify we have both types
    assert scored_count > 0, "Should have scored criteria"
    assert checklist_count > 0, "Should have checklist criteria"
    
    print("\n✅ All tests passed! Explicit typing is working correctly.")


if __name__ == "__main__":
    test_explicit_typing()