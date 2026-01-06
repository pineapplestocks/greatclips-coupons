#!/usr/bin/env python3
"""
Replace the scissors emoji (✂️) with the mascot logo in ALL HTML files.
Run this once to update all existing pages.
"""

import os
from pathlib import Path

DOCS_DIR = "docs"

# Old code to find
OLD_LOGO = '''<span class="text-2xl">✂️</span>
                    <span class="font-bold text-lg text-purple-600">GreatClipsDeal</span>'''

# New code with image logo
NEW_LOGO = '''<img src="/logo.png" alt="GreatClipsDeal" class="h-8 w-8 rounded-full object-cover">
                    <span class="font-bold text-lg text-purple-600">GreatClipsDeal</span>'''

# Alternative patterns (different spacing/formatting)
OLD_PATTERNS = [
    # Pattern 1: Standard
    ('<span class="text-2xl">✂️</span>', '<img src="/logo.png" alt="GreatClipsDeal" class="h-8 w-8 rounded-full object-cover">'),
    # Pattern 2: With newlines
    ('<span class="text-2xl">✂️</span>\n', '<img src="/logo.png" alt="GreatClipsDeal" class="h-8 w-8 rounded-full object-cover">\n'),
    # Pattern 3: Just the emoji in a span
    ('class="text-2xl">✂️<', 'src="/logo.png" alt="GreatClipsDeal" class="h-8 w-8 rounded-full object-cover"><'),
]

def update_file(filepath):
    """Update a single HTML file to use the new logo"""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
        
        original_content = content
        
        # Try each pattern
        for old, new in OLD_PATTERNS:
            content = content.replace(old, new)
        
        # Check if anything changed
        if content != original_content:
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(content)
            return True
        return False
    except Exception as e:
        print(f"  Error processing {filepath}: {e}")
        return False

def main():
    docs_path = Path(DOCS_DIR)
    
    if not docs_path.exists():
        print(f"Error: {DOCS_DIR} directory not found")
        return
    
    # Find all HTML files
    html_files = list(docs_path.rglob("*.html"))
    
    print(f"Found {len(html_files)} HTML files")
    print("=" * 50)
    
    updated = 0
    skipped = 0
    
    for filepath in html_files:
        if update_file(filepath):
            print(f"✓ Updated: {filepath}")
            updated += 1
        else:
            skipped += 1
    
    print("=" * 50)
    print(f"✅ Updated: {updated} files")
    print(f"⏭️  Skipped: {skipped} files (already updated or no match)")
    print("\n⚠️  Don't forget to upload logo.png to your docs/ folder!")

if __name__ == "__main__":
    main()
