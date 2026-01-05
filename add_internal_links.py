#!/usr/bin/env python3
"""
Add comprehensive internal linking to all pages
- Adds footer with links to all major sections
- Adds related content sections
- Improves SEO link juice flow
"""

import os
import re

# ============================================================================
# COMPREHENSIVE FOOTER WITH INTERNAL LINKS
# ============================================================================

FOOTER_HTML = '''
    <!-- Internal Links Footer -->
    <section class="bg-slate-100 py-12">
        <div class="max-w-6xl mx-auto px-4">
            <div class="grid md:grid-cols-4 gap-8">
                <!-- Popular Coupons -->
                <div>
                    <h3 class="font-bold text-slate-900 mb-4">Popular Coupons</h3>
                    <ul class="space-y-2 text-sm">
                        <li><a href="/5-99-coupon" class="text-slate-600 hover:text-purple-600">$5.99 Haircut Coupon</a></li>
                        <li><a href="/6-99-coupon" class="text-slate-600 hover:text-purple-600">$6.99 Haircut Coupon</a></li>
                        <li><a href="/prices" class="text-slate-600 hover:text-purple-600">Great Clips Prices</a></li>
                        <li><a href="/how-to-use" class="text-slate-600 hover:text-purple-600">How to Use Coupons</a></li>
                    </ul>
                </div>
                
                <!-- Top States -->
                <div>
                    <h3 class="font-bold text-slate-900 mb-4">Top States</h3>
                    <ul class="space-y-2 text-sm">
                        <li><a href="/texas" class="text-slate-600 hover:text-purple-600">Texas Coupons</a></li>
                        <li><a href="/california" class="text-slate-600 hover:text-purple-600">California Coupons</a></li>
                        <li><a href="/florida" class="text-slate-600 hover:text-purple-600">Florida Coupons</a></li>
                        <li><a href="/ohio" class="text-slate-600 hover:text-purple-600">Ohio Coupons</a></li>
                        <li><a href="/states" class="text-slate-600 hover:text-purple-600">All States →</a></li>
                    </ul>
                </div>
                
                <!-- Major Cities -->
                <div>
                    <h3 class="font-bold text-slate-900 mb-4">Major Cities</h3>
                    <ul class="space-y-2 text-sm">
                        <li><a href="/cities/houston" class="text-slate-600 hover:text-purple-600">Houston</a></li>
                        <li><a href="/cities/dallas" class="text-slate-600 hover:text-purple-600">Dallas</a></li>
                        <li><a href="/cities/chicago" class="text-slate-600 hover:text-purple-600">Chicago</a></li>
                        <li><a href="/cities/phoenix" class="text-slate-600 hover:text-purple-600">Phoenix</a></li>
                        <li><a href="/cities/atlanta" class="text-slate-600 hover:text-purple-600">Atlanta</a></li>
                    </ul>
                </div>
                
                <!-- Resources -->
                <div>
                    <h3 class="font-bold text-slate-900 mb-4">Resources</h3>
                    <ul class="space-y-2 text-sm">
                        <li><a href="/blog/great-clips-prices-2026" class="text-slate-600 hover:text-purple-600">Price Guide 2026</a></li>
                        <li><a href="/blog/great-clips-vs-supercuts" class="text-slate-600 hover:text-purple-600">Great Clips vs Supercuts</a></li>
                        <li><a href="/blog/great-clips-senior-discount" class="text-slate-600 hover:text-purple-600">Senior Discount Guide</a></li>
                        <li><a href="/" class="text-slate-600 hover:text-purple-600">All Coupons</a></li>
                    </ul>
                </div>
            </div>
            
            <!-- More States Row -->
            <div class="mt-8 pt-8 border-t border-slate-200">
                <h3 class="font-bold text-slate-900 mb-4">More States</h3>
                <div class="flex flex-wrap gap-2 text-sm">
                    <a href="/michigan" class="text-slate-600 hover:text-purple-600">Michigan</a> •
                    <a href="/pennsylvania" class="text-slate-600 hover:text-purple-600">Pennsylvania</a> •
                    <a href="/illinois" class="text-slate-600 hover:text-purple-600">Illinois</a> •
                    <a href="/georgia" class="text-slate-600 hover:text-purple-600">Georgia</a> •
                    <a href="/north-carolina" class="text-slate-600 hover:text-purple-600">North Carolina</a> •
                    <a href="/arizona" class="text-slate-600 hover:text-purple-600">Arizona</a> •
                    <a href="/minnesota" class="text-slate-600 hover:text-purple-600">Minnesota</a> •
                    <a href="/indiana" class="text-slate-600 hover:text-purple-600">Indiana</a> •
                    <a href="/wisconsin" class="text-slate-600 hover:text-purple-600">Wisconsin</a> •
                    <a href="/colorado" class="text-slate-600 hover:text-purple-600">Colorado</a> •
                    <a href="/tennessee" class="text-slate-600 hover:text-purple-600">Tennessee</a> •
                    <a href="/virginia" class="text-slate-600 hover:text-purple-600">Virginia</a> •
                    <a href="/washington" class="text-slate-600 hover:text-purple-600">Washington</a> •
                    <a href="/new-york" class="text-slate-600 hover:text-purple-600">New York</a>
                </div>
            </div>
            
            <!-- More Cities Row -->
            <div class="mt-6">
                <h3 class="font-bold text-slate-900 mb-4">More Cities</h3>
                <div class="flex flex-wrap gap-2 text-sm">
                    <a href="/cities/columbus" class="text-slate-600 hover:text-purple-600">Columbus</a> •
                    <a href="/cities/denver" class="text-slate-600 hover:text-purple-600">Denver</a> •
                    <a href="/cities/minneapolis" class="text-slate-600 hover:text-purple-600">Minneapolis</a> •
                    <a href="/cities/detroit" class="text-slate-600 hover:text-purple-600">Detroit</a> •
                    <a href="/cities/indianapolis" class="text-slate-600 hover:text-purple-600">Indianapolis</a>
                </div>
            </div>
        </div>
    </section>

    <footer class="bg-slate-900 text-white py-12">
        <div class="max-w-4xl mx-auto px-4 text-center">
            <p class="text-slate-400 mb-4">Updated daily with official Great Clips coupons</p>
            <div class="flex justify-center gap-4 text-sm mb-4">
                <a href="/" class="text-purple-400 hover:text-purple-300">Home</a>
                <a href="/states" class="text-purple-400 hover:text-purple-300">States</a>
                <a href="/prices" class="text-purple-400 hover:text-purple-300">Prices</a>
                <a href="/how-to-use" class="text-purple-400 hover:text-purple-300">How to Use</a>
            </div>
            <a href="/" class="text-purple-400 hover:text-purple-300 font-bold">GreatClipsDeal.com</a>
        </div>
    </footer>
</body>
</html>'''

# Related content for state pages
def get_related_states(state_slug):
    """Get nearby/related states for internal linking"""
    related = {
        'ohio': ['michigan', 'indiana', 'pennsylvania', 'kentucky'],
        'michigan': ['ohio', 'indiana', 'wisconsin', 'illinois'],
        'pennsylvania': ['ohio', 'new-york', 'new-jersey', 'maryland'],
        'illinois': ['indiana', 'wisconsin', 'michigan', 'missouri'],
        'georgia': ['florida', 'tennessee', 'north-carolina', 'alabama'],
        'north-carolina': ['virginia', 'georgia', 'tennessee', 'south-carolina'],
        'arizona': ['california', 'nevada', 'colorado', 'new-mexico'],
        'minnesota': ['wisconsin', 'iowa', 'north-dakota', 'south-dakota'],
        'indiana': ['ohio', 'michigan', 'illinois', 'kentucky'],
        'wisconsin': ['minnesota', 'michigan', 'illinois', 'iowa'],
        'colorado': ['arizona', 'utah', 'kansas', 'nebraska'],
        'tennessee': ['georgia', 'north-carolina', 'virginia', 'kentucky'],
        'virginia': ['north-carolina', 'maryland', 'west-virginia', 'tennessee'],
        'washington': ['oregon', 'california', 'idaho', 'montana'],
        'new-york': ['pennsylvania', 'new-jersey', 'connecticut', 'massachusetts'],
        'texas': ['oklahoma', 'louisiana', 'new-mexico', 'arkansas'],
        'california': ['arizona', 'nevada', 'oregon', 'washington'],
        'florida': ['georgia', 'alabama', 'south-carolina', 'tennessee'],
    }
    return related.get(state_slug, ['texas', 'california', 'florida', 'ohio'])

# State name mapping
STATE_NAMES = {
    'ohio': 'Ohio', 'michigan': 'Michigan', 'pennsylvania': 'Pennsylvania',
    'illinois': 'Illinois', 'georgia': 'Georgia', 'north-carolina': 'North Carolina',
    'arizona': 'Arizona', 'minnesota': 'Minnesota', 'indiana': 'Indiana',
    'wisconsin': 'Wisconsin', 'colorado': 'Colorado', 'tennessee': 'Tennessee',
    'virginia': 'Virginia', 'washington': 'Washington', 'new-york': 'New York',
    'texas': 'Texas', 'california': 'California', 'florida': 'Florida',
    'kentucky': 'Kentucky', 'missouri': 'Missouri', 'alabama': 'Alabama',
    'new-jersey': 'New Jersey', 'maryland': 'Maryland', 'nevada': 'Nevada',
    'new-mexico': 'New Mexico', 'iowa': 'Iowa', 'north-dakota': 'North Dakota',
    'south-dakota': 'South Dakota', 'utah': 'Utah', 'kansas': 'Kansas',
    'nebraska': 'Nebraska', 'oregon': 'Oregon', 'idaho': 'Idaho',
    'montana': 'Montana', 'connecticut': 'Connecticut', 'massachusetts': 'Massachusetts',
    'oklahoma': 'Oklahoma', 'louisiana': 'Louisiana', 'arkansas': 'Arkansas',
    'south-carolina': 'South Carolina', 'west-virginia': 'West Virginia',
}

def update_state_page(filepath, state_slug):
    """Update state page with better internal linking"""
    with open(filepath, 'r') as f:
        content = f.read()
    
    # Get related states
    related = get_related_states(state_slug)
    
    # Create related states section
    related_html = '''
        <!-- Related States -->
        <div class="bg-white rounded-xl p-8 shadow-md mb-12">
            <h2 class="text-2xl font-bold text-slate-900 mb-6">Nearby States</h2>
            <div class="grid grid-cols-2 md:grid-cols-4 gap-4">
'''
    for rel_slug in related[:4]:
        name = STATE_NAMES.get(rel_slug, rel_slug.replace('-', ' ').title())
        related_html += f'''                <a href="/{rel_slug}" class="bg-slate-50 hover:bg-purple-50 p-4 rounded-lg text-center transition-colors">
                    <span class="font-medium text-slate-900">{name}</span>
                    <span class="block text-sm text-slate-500">Coupons</span>
                </a>
'''
    related_html += '''            </div>
        </div>

        <!-- Helpful Resources -->
        <div class="bg-white rounded-xl p-8 shadow-md mb-12">
            <h2 class="text-2xl font-bold text-slate-900 mb-6">Helpful Resources</h2>
            <div class="grid md:grid-cols-3 gap-4">
                <a href="/blog/great-clips-prices-2026" class="block p-4 border rounded-lg hover:border-purple-300 hover:bg-purple-50 transition-colors">
                    <span class="font-bold text-slate-900">Price Guide 2026</span>
                    <span class="block text-sm text-slate-500">Complete price list</span>
                </a>
                <a href="/blog/great-clips-senior-discount" class="block p-4 border rounded-lg hover:border-purple-300 hover:bg-purple-50 transition-colors">
                    <span class="font-bold text-slate-900">Senior Discount</span>
                    <span class="block text-sm text-slate-500">65+ savings guide</span>
                </a>
                <a href="/how-to-use" class="block p-4 border rounded-lg hover:border-purple-300 hover:bg-purple-50 transition-colors">
                    <span class="font-bold text-slate-900">How to Use</span>
                    <span class="block text-sm text-slate-500">Step-by-step guide</span>
                </a>
            </div>
        </div>
'''
    
    # Find the "Other States" section and replace it with our enhanced version
    pattern = r'<!-- Other States -->.*?</div>\s*</div>\s*</main>'
    replacement = related_html + '\n    </main>'
    content = re.sub(pattern, replacement, content, flags=re.DOTALL)
    
    # Replace old footer with comprehensive footer
    content = re.sub(r'<footer class="bg-slate-900.*?</html>', FOOTER_HTML, content, flags=re.DOTALL)
    
    with open(filepath, 'w') as f:
        f.write(content)
    
    print(f"  Updated: {filepath}")

def update_city_page(filepath):
    """Update city page with better internal linking"""
    with open(filepath, 'r') as f:
        content = f.read()
    
    # Add resources section before Related section
    resources_html = '''
        <!-- Helpful Resources -->
        <div class="bg-white rounded-xl p-8 shadow-md mb-12">
            <h2 class="text-2xl font-bold text-slate-900 mb-6">Helpful Resources</h2>
            <div class="grid md:grid-cols-3 gap-4">
                <a href="/blog/great-clips-prices-2026" class="block p-4 border rounded-lg hover:border-purple-300 hover:bg-purple-50 transition-colors">
                    <span class="font-bold text-slate-900">Price Guide</span>
                    <span class="block text-sm text-slate-500">2026 prices</span>
                </a>
                <a href="/blog/great-clips-senior-discount" class="block p-4 border rounded-lg hover:border-purple-300 hover:bg-purple-50 transition-colors">
                    <span class="font-bold text-slate-900">Senior Discount</span>
                    <span class="block text-sm text-slate-500">65+ savings</span>
                </a>
                <a href="/5-99-coupon" class="block p-4 border rounded-lg hover:border-purple-300 hover:bg-purple-50 transition-colors">
                    <span class="font-bold text-slate-900">$5.99 Coupon</span>
                    <span class="block text-sm text-slate-500">Best deal</span>
                </a>
            </div>
        </div>

'''
    
    # Insert before Related section
    content = content.replace('<!-- Related -->', resources_html + '<!-- Related -->')
    
    # Replace old footer with comprehensive footer
    content = re.sub(r'<footer class="bg-slate-900.*?</html>', FOOTER_HTML, content, flags=re.DOTALL)
    
    with open(filepath, 'w') as f:
        f.write(content)
    
    print(f"  Updated: {filepath}")

def update_blog_page(filepath):
    """Update blog page with internal links"""
    with open(filepath, 'r') as f:
        content = f.read()
    
    # Replace old footer with comprehensive footer
    content = re.sub(r'<footer class="bg-slate-900.*?</html>', FOOTER_HTML, content, flags=re.DOTALL)
    
    with open(filepath, 'w') as f:
        f.write(content)
    
    print(f"  Updated: {filepath}")

def main():
    print("=" * 60)
    print("Adding Internal Links to All Pages")
    print("=" * 60)
    
    # Update state pages
    print("\nUpdating State Pages...")
    state_files = [
        'pages/ohio.html', 'pages/michigan.html', 'pages/pennsylvania.html',
        'pages/illinois.html', 'pages/georgia.html', 'pages/north-carolina.html',
        'pages/arizona.html', 'pages/minnesota.html', 'pages/indiana.html',
        'pages/wisconsin.html', 'pages/colorado.html', 'pages/tennessee.html',
        'pages/virginia.html', 'pages/washington.html', 'pages/new-york.html',
        'pages/texas.html', 'pages/california.html', 'pages/florida.html'
    ]
    for filepath in state_files:
        if os.path.exists(filepath):
            state_slug = os.path.basename(filepath).replace('.html', '')
            update_state_page(filepath, state_slug)
    
    # Update city pages
    print("\nUpdating City Pages...")
    for filename in os.listdir('pages/cities'):
        if filename.endswith('.html'):
            update_city_page(f'pages/cities/{filename}')
    
    # Update blog pages
    print("\nUpdating Blog Pages...")
    for filename in os.listdir('pages/blog'):
        if filename.endswith('.html'):
            update_blog_page(f'pages/blog/{filename}')
    
    print("\n" + "=" * 60)
    print("✅ Internal linking added to all pages!")
    print("=" * 60)

if __name__ == "__main__":
    main()
