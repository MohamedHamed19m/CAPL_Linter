"""
Inspect what's actually in the project files
"""

from pathlib import Path
import re


def check_file_content(file_path, search_patterns):
    """Check if patterns exist in a file"""
    path = Path(file_path)
    
    if not path.exists():
        print(f"❌ {file_path} NOT FOUND")
        return
    
    print(f"\n{'=' * 70}")
    print(f"📄 {file_path}")
    print('=' * 70)
    
    with open(path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    print(f"File size: {len(content)} characters, {len(content.splitlines())} lines")
    
    for pattern_name, pattern in search_patterns.items():
        if re.search(pattern, content, re.MULTILINE):
            print(f"✓ Found: {pattern_name}")
            
            # Show context
            matches = re.finditer(pattern, content, re.MULTILINE)
            for match in matches:
                # Find line number
                line_num = content[:match.start()].count('\n') + 1
                print(f"  → Line {line_num}")
                break
        else:
            print(f"❌ Missing: {pattern_name}")


def list_classes_and_functions(file_path):
    """List all classes and functions in a file"""
    path = Path(file_path)
    
    if not path.exists():
        return
    
    with open(path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Find classes
    classes = re.findall(r'^class\s+(\w+)', content, re.MULTILINE)
    if classes:
        print(f"\n📦 Classes found: {', '.join(classes)}")
    else:
        print(f"\n📦 No classes found")
    
    # Find functions (not methods)
    functions = re.findall(r'^def\s+(\w+)\s*\(', content, re.MULTILINE)
    if functions:
        print(f"🔧 Top-level functions found: {', '.join(functions[:10])}")
        if len(functions) > 10:
            print(f"   ... and {len(functions) - 10} more")
    else:
        print(f"🔧 No top-level functions found")


def main():
    print("🔍 INSPECTING CAPL ANALYZER PROJECT FILES\n")
    
    # Check linter.py
    linter_patterns = {
        'CAPLLinter class': r'^class\s+CAPLLinter',
        'main() function': r'^def\s+main\s*\(',
        'LintIssue class': r'^class\s+LintIssue',
        'Severity class': r'^class\s+Severity',
    }
    
    check_file_content('src/capl_analyzer/linter.py', linter_patterns)
    list_classes_and_functions('src/capl_analyzer/linter.py')
    
    # Check __init__.py
    init_patterns = {
        'from .linter import': r'from \.linter import',
        'CAPLLinter in imports': r'CAPLLinter',
    }
    
    check_file_content('src/capl_analyzer/__init__.py', init_patterns)
    
    # Check other modules
    for module in ['dependency_analyzer.py', 'symbol_extractor.py', 'cross_reference.py']:
        module_path = f'src/capl_analyzer/{module}'
        if Path(module_path).exists():
            print(f"\n{'=' * 70}")
            print(f"📄 {module}")
            print('=' * 70)
            list_classes_and_functions(module_path)
    
    # Show file tree
    print(f"\n{'=' * 70}")
    print("📁 PROJECT STRUCTURE")
    print('=' * 70)
    
    src_dir = Path('src/capl_analyzer')
    if src_dir.exists():
        for file in sorted(src_dir.glob('*.py')):
            size = file.stat().st_size
            print(f"  {file.name:30s} {size:>8,} bytes")
    
    print(f"\n{'=' * 70}")
    print("💡 DIAGNOSIS")
    print('=' * 70)
    
    # Check if linter.py has content
    linter_path = Path('src/capl_analyzer/linter.py')
    if linter_path.exists():
        with open(linter_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        if 'class CAPLLinter' not in content:
            print("\n❌ PROBLEM: linter.py doesn't contain CAPLLinter class!")
            print("   The file might be empty or have wrong content.")
            print("\n   Possible causes:")
            print("   1. File wasn't copied/created properly")
            print("   2. Wrong file content")
            print("\n   Solution:")
            print("   The linter.py file needs the full implementation.")
            print("   You need to copy the complete code from the artifacts.")
        else:
            print("\n✓ linter.py has CAPLLinter class")
            
            if 'def main():' not in content:
                print("❌ But main() function is missing!")
            else:
                print("✓ main() function exists")


if __name__ == "__main__":
    main()