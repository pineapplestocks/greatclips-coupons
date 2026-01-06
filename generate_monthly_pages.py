#!/usr/bin/env python3
"""
Auto-generate monthly Great Clips coupon landing pages.
Runs on the 1st of each month via GitHub Actions.
"""

import os
from datetime import datetime, timedelta
from pathlib import Path

# Configuration
OUTPUT_DIR = "docs"  # Where pages are served from
SITE_URL = "https://greatclipsdeal.com"

MONTH_NAMES = [
    "January", "February", "March", "April", "May", "June",
    "July", "August", "September", "October", "November", "December"
]

def get_month_slug(month, year):
    """Generate URL slug like 'january-2026'"""
    return f"{MONTH_NAMES[month-1].lower()}-{year}"

def get_adjacent_months(month, year):
    """Get previous and next month info"""
    # Previous month
    if month == 1:
        prev_month, prev_year = 12, year - 1
    else:
        prev_month, prev_year = month - 1, year
    
    # Next month
    if month == 12:
        next_month, next_year = 1, year + 1
    else:
        next_month, next_year = month + 1, year
    
    return {
        'prev': {'month': prev_month, 'year': prev_year, 'name': MONTH_NAMES[prev_month-1], 'slug': get_month_slug(prev_month, prev_year)},
        'next': {'month': next_month, 'year': next_year, 'name': MONTH_NAMES[next_month-1], 'slug': get_month_slug(next_month, next_year)}
    }

def generate_monthly_page(month, year):
    """Generate HTML for a monthly landing page"""
    month_name = MONTH_NAMES[month - 1]
    slug = get_month_slug(month, year)
    adjacent = get_adjacent_months(month, year)
    
    # Seasonal messaging
    seasonal_tips = {
        1: "Start the new year with a fresh look! Great Clips offers amazing January deals.",
        2: "Look your best for Valentine's Day with a fresh haircut at Great Clips.",
        3: "Spring is here! Time for a fresh cut at Great Clips.",
        4: "April showers bring May flowers—and great haircuts at Great Clips!",
        5: "Get ready for summer with a stylish cut from Great Clips.",
        6: "Summer is here! Beat the heat with a cool new style.",
        7: "Mid-summer deals are hot! Save on haircuts this July.",
        8: "Back-to-school season means it's time for fresh haircuts!",
        9: "Fall into savings with September Great Clips coupons.",
        10: "October deals are here—look great for Halloween and beyond!",
        11: "Get holiday-ready with November haircut deals.",
        12: "End the year looking great with December savings!"
    }
    
    html = f'''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    
    <!-- Google tag (gtag.js) -->
    <script async src="https://www.googletagmanager.com/gtag/js?id=G-90ZQ7M4EFR"></script>
    <script>
      window.dataLayer = window.dataLayer || [];
      function gtag(){{dataLayer.push(arguments);}}
      gtag('js', new Date());
      gtag('config', 'G-90ZQ7M4EFR');
    </script>
    
    <title>Great Clips Coupons {month_name} {year} - $5.99 Haircut Deals</title>
    <meta name="description" content="Find working Great Clips coupons for {month_name} {year}. Save $5-$10 on haircuts with daily updated {month_name} coupon codes. Valid at 4,400+ US locations.">
    <meta name="keywords" content="Great Clips coupons {month_name} {year}, Great Clips {month_name} {year}, haircut coupons {month_name}, Great Clips deals {month_name} {year}">
    <link rel="canonical" href="{SITE_URL}/{slug}">
    
    <!-- Open Graph -->
    <meta property="og:title" content="Great Clips Coupons {month_name} {year} - $5.99 Haircut Deals">
    <meta property="og:description" content="Find working Great Clips coupons for {month_name} {year}. Save $5-$10 on haircuts.">
    <meta property="og:url" content="{SITE_URL}/{slug}">
    <meta property="og:type" content="website">
    
    <!-- Favicon -->
    <link rel="icon" type="image/svg+xml" href="/favicon.svg">
    
    <script src="https://cdn.tailwindcss.com"></script>
    <link href="https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800&display=swap" rel="stylesheet">
    <style>
        body {{ font-family: 'Plus Jakarta Sans', sans-serif; }}
    </style>
    
    <!-- Schema.org markup -->
    <script type="application/ld+json">
    {{
        "@context": "https://schema.org",
        "@type": "WebPage",
        "name": "Great Clips Coupons {month_name} {year}",
        "description": "Find working Great Clips coupons for {month_name} {year}. Daily updated haircut deals.",
        "url": "{SITE_URL}/{slug}",
        "dateModified": "{year}-{month:02d}-01",
        "publisher": {{
            "@type": "Organization",
            "name": "GreatClipsDeal",
            "url": "{SITE_URL}"
        }}
    }}
    </script>
</head>
<body class="bg-gradient-to-br from-slate-50 to-slate-100 min-h-screen">
    <!-- Navigation -->
    <nav class="bg-white/95 backdrop-blur-sm shadow-sm sticky top-0 z-50 border-b border-slate-100">
        <div class="max-w-6xl mx-auto px-4">
            <div class="flex justify-between items-center h-14">
                <a href="/" class="flex items-center gap-2">
                    <img src="/logo.png" alt="GreatClipsDeal" class="h-8 w-8 rounded-full object-cover">
                    <span class="font-bold text-lg text-purple-600">GreatClipsDeal</span>
                </a>
                <div class="hidden md:flex items-center gap-6 text-sm">
                    <a href="/states" class="text-slate-600 hover:text-purple-600 font-medium">Browse by State</a>
                    <a href="/calculator" class="text-slate-600 hover:text-purple-600 font-medium">Savings Calculator</a>
                    <a href="/faq" class="text-slate-600 hover:text-purple-600 font-medium">FAQ</a>
                </div>
            </div>
        </div>
    </nav>

    <!-- Breadcrumb -->
    <div class="max-w-6xl mx-auto px-4 py-3">
        <nav class="text-sm text-slate-500">
            <a href="/" class="hover:text-purple-600">Home</a>
            <span class="mx-2">›</span>
            <span class="text-slate-900">{month_name} {year} Coupons</span>
        </nav>
    </div>

    <!-- Hero Section -->
    <header class="bg-gradient-to-r from-violet-600 to-purple-600 text-white py-12">
        <div class="max-w-6xl mx-auto px-4 text-center">
            <div class="inline-flex items-center gap-2 bg-white/20 rounded-full px-4 py-1.5 mb-4">
                <span class="w-2 h-2 bg-emerald-400 rounded-full animate-pulse"></span>
                <span class="text-sm font-medium">Updated Daily</span>
            </div>
            <h1 class="text-4xl md:text-5xl font-extrabold mb-4">
                Great Clips Coupons {month_name} {year}
            </h1>
            <p class="text-xl text-white/80 max-w-2xl mx-auto">
                {seasonal_tips.get(month, "Find the best Great Clips deals this month!")}
            </p>
        </div>
    </header>

    <!-- Main Content -->
    <main class="max-w-6xl mx-auto px-4 py-10">
        <!-- CTA Section -->
        <section class="bg-white rounded-2xl shadow-lg p-8 mb-10 text-center">
            <h2 class="text-2xl font-bold text-slate-900 mb-4">
                🎉 {month_name} {year} Coupons Available Now!
            </h2>
            <p class="text-slate-600 mb-6 max-w-2xl mx-auto">
                We update our coupon database daily with the latest Great Clips deals. 
                Click below to see all available coupons for {month_name} {year}.
            </p>
            <a href="/" class="inline-block bg-gradient-to-r from-violet-600 to-purple-600 hover:from-violet-700 hover:to-purple-700 text-white font-bold py-4 px-8 rounded-xl text-lg transition-all shadow-lg shadow-purple-200">
                View All {month_name} Coupons →
            </a>
        </section>

        <!-- Stats Grid -->
        <section class="grid grid-cols-1 md:grid-cols-3 gap-6 mb-10">
            <div class="bg-white rounded-xl p-6 text-center shadow-sm">
                <div class="text-4xl font-bold text-purple-600 mb-2">$5.99</div>
                <div class="text-slate-600">Lowest Price Available</div>
            </div>
            <div class="bg-white rounded-xl p-6 text-center shadow-sm">
                <div class="text-4xl font-bold text-purple-600 mb-2">50+</div>
                <div class="text-slate-600">Active Coupons</div>
            </div>
            <div class="bg-white rounded-xl p-6 text-center shadow-sm">
                <div class="text-4xl font-bold text-purple-600 mb-2">4,400+</div>
                <div class="text-slate-600">US Locations</div>
            </div>
        </section>

        <!-- What to Expect -->
        <section class="bg-white rounded-2xl shadow-sm p-8 mb-10">
            <h2 class="text-2xl font-bold text-slate-900 mb-6">
                What to Expect in {month_name} {year}
            </h2>
            <div class="grid md:grid-cols-2 gap-6">
                <div class="flex gap-4">
                    <div class="w-10 h-10 bg-purple-100 rounded-lg flex items-center justify-center flex-shrink-0">
                        <span class="text-xl">💰</span>
                    </div>
                    <div>
                        <h3 class="font-semibold text-slate-900 mb-1">$5.99 - $8.99 Deals</h3>
                        <p class="text-slate-600 text-sm">Most {month_name} coupons offer haircuts between $5.99 and $8.99, saving you up to $10 per visit.</p>
                    </div>
                </div>
                <div class="flex gap-4">
                    <div class="w-10 h-10 bg-purple-100 rounded-lg flex items-center justify-center flex-shrink-0">
                        <span class="text-xl">📍</span>
                    </div>
                    <div>
                        <h3 class="font-semibold text-slate-900 mb-1">Location-Specific Deals</h3>
                        <p class="text-slate-600 text-sm">Some coupons are valid at specific salons. Filter by your state to find local deals.</p>
                    </div>
                </div>
                <div class="flex gap-4">
                    <div class="w-10 h-10 bg-purple-100 rounded-lg flex items-center justify-center flex-shrink-0">
                        <span class="text-xl">⏰</span>
                    </div>
                    <div>
                        <h3 class="font-semibold text-slate-900 mb-1">14-Day Validity</h3>
                        <p class="text-slate-600 text-sm">Once you click a coupon, it's typically valid for 14 days. Plan your visit accordingly!</p>
                    </div>
                </div>
                <div class="flex gap-4">
                    <div class="w-10 h-10 bg-purple-100 rounded-lg flex items-center justify-center flex-shrink-0">
                        <span class="text-xl">🔄</span>
                    </div>
                    <div>
                        <h3 class="font-semibold text-slate-900 mb-1">Daily Updates</h3>
                        <p class="text-slate-600 text-sm">We scan for new coupons every day, so check back often for fresh deals.</p>
                    </div>
                </div>
            </div>
        </section>

        <!-- Month Navigation -->
        <section class="flex justify-between items-center bg-white rounded-xl shadow-sm p-4 mb-10">
            <a href="/{adjacent['prev']['slug']}" class="flex items-center gap-2 text-purple-600 hover:text-purple-700 font-medium">
                <span>←</span>
                <span>{adjacent['prev']['name']} {adjacent['prev']['year']}</span>
            </a>
            <span class="text-slate-400">Browse by Month</span>
            <a href="/{adjacent['next']['slug']}" class="flex items-center gap-2 text-purple-600 hover:text-purple-700 font-medium">
                <span>{adjacent['next']['name']} {adjacent['next']['year']}</span>
                <span>→</span>
            </a>
        </section>

        <!-- Popular States -->
        <section class="bg-white rounded-2xl shadow-sm p-8 mb-10">
            <h2 class="text-2xl font-bold text-slate-900 mb-6">
                {month_name} Coupons by State
            </h2>
            <div class="grid grid-cols-2 md:grid-cols-4 gap-3">
                <a href="/texas" class="bg-slate-50 hover:bg-purple-50 rounded-lg p-3 text-center font-medium text-slate-700 hover:text-purple-600 transition-colors">Texas</a>
                <a href="/california" class="bg-slate-50 hover:bg-purple-50 rounded-lg p-3 text-center font-medium text-slate-700 hover:text-purple-600 transition-colors">California</a>
                <a href="/florida" class="bg-slate-50 hover:bg-purple-50 rounded-lg p-3 text-center font-medium text-slate-700 hover:text-purple-600 transition-colors">Florida</a>
                <a href="/ohio" class="bg-slate-50 hover:bg-purple-50 rounded-lg p-3 text-center font-medium text-slate-700 hover:text-purple-600 transition-colors">Ohio</a>
                <a href="/michigan" class="bg-slate-50 hover:bg-purple-50 rounded-lg p-3 text-center font-medium text-slate-700 hover:text-purple-600 transition-colors">Michigan</a>
                <a href="/arizona" class="bg-slate-50 hover:bg-purple-50 rounded-lg p-3 text-center font-medium text-slate-700 hover:text-purple-600 transition-colors">Arizona</a>
                <a href="/georgia" class="bg-slate-50 hover:bg-purple-50 rounded-lg p-3 text-center font-medium text-slate-700 hover:text-purple-600 transition-colors">Georgia</a>
                <a href="/states" class="bg-purple-100 hover:bg-purple-200 rounded-lg p-3 text-center font-medium text-purple-700 transition-colors">All 50 States →</a>
            </div>
        </section>

        <!-- FAQ Section -->
        <section class="bg-white rounded-2xl shadow-sm p-8">
            <h2 class="text-2xl font-bold text-slate-900 mb-6">
                {month_name} {year} FAQs
            </h2>
            <div class="space-y-6">
                <div>
                    <h3 class="font-semibold text-slate-900 mb-2">Are {month_name} {year} Great Clips coupons still valid?</h3>
                    <p class="text-slate-600">Yes! We update our coupon database daily. All coupons shown on our site are currently active and sourced from official Great Clips Facebook ads.</p>
                </div>
                <div>
                    <h3 class="font-semibold text-slate-900 mb-2">What's the best Great Clips deal in {month_name} {year}?</h3>
                    <p class="text-slate-600">The best deals are typically $5.99-$6.99 haircut coupons. Check our homepage for the current lowest prices available in your area.</p>
                </div>
                <div>
                    <h3 class="font-semibold text-slate-900 mb-2">How do I use a {month_name} coupon?</h3>
                    <p class="text-slate-600">Simply click the coupon on our site, save or screenshot it, and show it to your stylist before your haircut. <a href="/how-to-use" class="text-purple-600 hover:underline">See our full guide</a>.</p>
                </div>
            </div>
        </section>
    </main>

    <!-- Footer -->
    <footer class="bg-slate-900 text-slate-400 py-10 mt-10">
        <div class="max-w-6xl mx-auto px-4">
            <div class="grid grid-cols-2 md:grid-cols-4 gap-8 mb-8">
                <div>
                    <h3 class="text-white font-bold mb-3">Popular Coupons</h3>
                    <ul class="space-y-2 text-sm">
                        <li><a href="/5-99-coupon" class="hover:text-purple-400">$5.99 Coupons</a></li>
                        <li><a href="/6-99-coupon" class="hover:text-purple-400">$6.99 Coupons</a></li>
                        <li><a href="/senior-discount" class="hover:text-purple-400">Senior Discounts</a></li>
                    </ul>
                </div>
                <div>
                    <h3 class="text-white font-bold mb-3">Top States</h3>
                    <ul class="space-y-2 text-sm">
                        <li><a href="/texas" class="hover:text-purple-400">Texas</a></li>
                        <li><a href="/california" class="hover:text-purple-400">California</a></li>
                        <li><a href="/florida" class="hover:text-purple-400">Florida</a></li>
                        <li><a href="/states" class="text-purple-400">All States →</a></li>
                    </ul>
                </div>
                <div>
                    <h3 class="text-white font-bold mb-3">Resources</h3>
                    <ul class="space-y-2 text-sm">
                        <li><a href="/how-to-use" class="hover:text-purple-400">How to Use</a></li>
                        <li><a href="/prices" class="hover:text-purple-400">Prices</a></li>
                        <li><a href="/faq" class="hover:text-purple-400">FAQ</a></li>
                    </ul>
                </div>
                <div>
                    <h3 class="text-white font-bold mb-3">Company</h3>
                    <ul class="space-y-2 text-sm">
                        <li><a href="/about" class="hover:text-purple-400">About</a></li>
                        <li><a href="/contact" class="hover:text-purple-400">Contact</a></li>
                        <li><a href="/privacy" class="hover:text-purple-400">Privacy</a></li>
                    </ul>
                </div>
            </div>
            <div class="border-t border-slate-800 pt-6 text-center text-sm">
                <p>© 2024-{year} GreatClipsDeal.com. Not affiliated with Great Clips Inc.</p>
            </div>
        </div>
    </footer>
</body>
</html>
'''
    return html, slug

def main():
    # Create output directory
    output_path = Path(OUTPUT_DIR)
    output_path.mkdir(exist_ok=True)
    
    # Get current date
    now = datetime.now()
    current_year = now.year
    current_month = now.month
    
    # Generate pages for:
    # - All remaining months of current year
    # - All months of next year
    pages_generated = []
    
    # Current year remaining months
    for month in range(current_month, 13):
        html, slug = generate_monthly_page(month, current_year)
        filepath = output_path / f"{slug}.html"
        with open(filepath, 'w') as f:
            f.write(html)
        pages_generated.append(f"{SITE_URL}/{slug}")
        print(f"✓ Generated {slug}.html")
    
    # Next year all months
    next_year = current_year + 1
    for month in range(1, 13):
        html, slug = generate_monthly_page(month, next_year)
        filepath = output_path / f"{slug}.html"
        with open(filepath, 'w') as f:
            f.write(html)
        pages_generated.append(f"{SITE_URL}/{slug}")
        print(f"✓ Generated {slug}.html")
    
    # Save list of generated URLs for indexing
    with open('generated_monthly_urls.txt', 'w') as f:
        f.write('\n'.join(pages_generated))
    
    print(f"\n✅ Generated {len(pages_generated)} monthly pages!")
    return pages_generated

if __name__ == "__main__":
    main()
