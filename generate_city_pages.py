#!/usr/bin/env python3
"""
Generate city landing pages for Great Clips coupons.
Targets major US metros for local SEO.
"""

from pathlib import Path

SITE_URL = "https://greatclipsdeal.com"
OUTPUT_DIR = "docs/cities"

# 50 additional cities (beyond the 10 you already have)
# Sorted by population/search volume potential
CITIES = [
    # Already have: Phoenix, Dallas, Houston, Chicago, Atlanta, Columbus, Indianapolis, Minneapolis, Denver, Detroit
    
    # Top 50 additional cities
    {"name": "Los Angeles", "state": "California", "state_abbr": "CA", "locations": "200+"},
    {"name": "New York City", "state": "New York", "state_abbr": "NY", "locations": "150+"},
    {"name": "San Antonio", "state": "Texas", "state_abbr": "TX", "locations": "80+"},
    {"name": "San Diego", "state": "California", "state_abbr": "CA", "locations": "70+"},
    {"name": "San Jose", "state": "California", "state_abbr": "CA", "locations": "50+"},
    {"name": "Austin", "state": "Texas", "state_abbr": "TX", "locations": "60+"},
    {"name": "Jacksonville", "state": "Florida", "state_abbr": "FL", "locations": "45+"},
    {"name": "Fort Worth", "state": "Texas", "state_abbr": "TX", "locations": "50+"},
    {"name": "Charlotte", "state": "North Carolina", "state_abbr": "NC", "locations": "55+"},
    {"name": "San Francisco", "state": "California", "state_abbr": "CA", "locations": "40+"},
    {"name": "Seattle", "state": "Washington", "state_abbr": "WA", "locations": "60+"},
    {"name": "Nashville", "state": "Tennessee", "state_abbr": "TN", "locations": "50+"},
    {"name": "Oklahoma City", "state": "Oklahoma", "state_abbr": "OK", "locations": "40+"},
    {"name": "Las Vegas", "state": "Nevada", "state_abbr": "NV", "locations": "55+"},
    {"name": "Portland", "state": "Oregon", "state_abbr": "OR", "locations": "45+"},
    {"name": "Milwaukee", "state": "Wisconsin", "state_abbr": "WI", "locations": "40+"},
    {"name": "Albuquerque", "state": "New Mexico", "state_abbr": "NM", "locations": "25+"},
    {"name": "Tucson", "state": "Arizona", "state_abbr": "AZ", "locations": "30+"},
    {"name": "Sacramento", "state": "California", "state_abbr": "CA", "locations": "45+"},
    {"name": "Kansas City", "state": "Missouri", "state_abbr": "MO", "locations": "50+"},
    {"name": "Mesa", "state": "Arizona", "state_abbr": "AZ", "locations": "25+"},
    {"name": "Virginia Beach", "state": "Virginia", "state_abbr": "VA", "locations": "30+"},
    {"name": "Omaha", "state": "Nebraska", "state_abbr": "NE", "locations": "30+"},
    {"name": "Colorado Springs", "state": "Colorado", "state_abbr": "CO", "locations": "25+"},
    {"name": "Raleigh", "state": "North Carolina", "state_abbr": "NC", "locations": "35+"},
    {"name": "Miami", "state": "Florida", "state_abbr": "FL", "locations": "60+"},
    {"name": "Tampa", "state": "Florida", "state_abbr": "FL", "locations": "50+"},
    {"name": "Orlando", "state": "Florida", "state_abbr": "FL", "locations": "55+"},
    {"name": "Cleveland", "state": "Ohio", "state_abbr": "OH", "locations": "45+"},
    {"name": "Pittsburgh", "state": "Pennsylvania", "state_abbr": "PA", "locations": "40+"},
    {"name": "Cincinnati", "state": "Ohio", "state_abbr": "OH", "locations": "40+"},
    {"name": "St Louis", "state": "Missouri", "state_abbr": "MO", "locations": "50+"},
    {"name": "Baltimore", "state": "Maryland", "state_abbr": "MD", "locations": "35+"},
    {"name": "Salt Lake City", "state": "Utah", "state_abbr": "UT", "locations": "40+"},
    {"name": "Richmond", "state": "Virginia", "state_abbr": "VA", "locations": "30+"},
    {"name": "Louisville", "state": "Kentucky", "state_abbr": "KY", "locations": "35+"},
    {"name": "Memphis", "state": "Tennessee", "state_abbr": "TN", "locations": "30+"},
    {"name": "Birmingham", "state": "Alabama", "state_abbr": "AL", "locations": "30+"},
    {"name": "Boise", "state": "Idaho", "state_abbr": "ID", "locations": "25+"},
    {"name": "Des Moines", "state": "Iowa", "state_abbr": "IA", "locations": "25+"},
    {"name": "Spokane", "state": "Washington", "state_abbr": "WA", "locations": "20+"},
    {"name": "Fresno", "state": "California", "state_abbr": "CA", "locations": "25+"},
    {"name": "Tulsa", "state": "Oklahoma", "state_abbr": "OK", "locations": "30+"},
    {"name": "Wichita", "state": "Kansas", "state_abbr": "KS", "locations": "25+"},
    {"name": "Arlington", "state": "Texas", "state_abbr": "TX", "locations": "30+"},
    {"name": "Bakersfield", "state": "California", "state_abbr": "CA", "locations": "20+"},
    {"name": "Aurora", "state": "Colorado", "state_abbr": "CO", "locations": "20+"},
    {"name": "Anaheim", "state": "California", "state_abbr": "CA", "locations": "25+"},
    {"name": "Honolulu", "state": "Hawaii", "state_abbr": "HI", "locations": "15+"},
    {"name": "Santa Ana", "state": "California", "state_abbr": "CA", "locations": "20+"},
]

def get_slug(city_name):
    """Convert city name to URL slug"""
    return city_name.lower().replace(" ", "-").replace(".", "")

def get_nearby_cities(current_city, all_cities):
    """Get 4 nearby cities (same state or neighboring)"""
    same_state = [c for c in all_cities if c["state"] == current_city["state"] and c["name"] != current_city["name"]]
    if len(same_state) >= 4:
        return same_state[:4]
    # Fill with other cities
    others = [c for c in all_cities if c["state"] != current_city["state"]][:4-len(same_state)]
    return same_state + others

def generate_city_page(city):
    """Generate HTML for a city landing page"""
    name = city["name"]
    state = city["state"]
    state_abbr = city["state_abbr"]
    locations = city["locations"]
    slug = get_slug(name)
    state_slug = state.lower().replace(" ", "-")
    
    nearby = get_nearby_cities(city, CITIES)[:4]
    
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
    
    <title>Great Clips Coupons {name} {state_abbr} - $5.99 Haircut Deals (2026)</title>
    <meta name="description" content="Find Great Clips coupons in {name}, {state}. Save $5-$10 on haircuts at {locations} {name} area locations. Daily updated {name} coupon codes.">
    <meta name="keywords" content="Great Clips {name}, Great Clips coupons {name}, Great Clips {name} {state_abbr}, haircut coupons {name}, cheap haircuts {name}">
    <link rel="canonical" href="{SITE_URL}/cities/{slug}">
    
    <!-- Open Graph -->
    <meta property="og:title" content="Great Clips Coupons {name} - $5.99 Haircut Deals">
    <meta property="og:description" content="Find Great Clips coupons in {name}, {state}. Save $5-$10 on haircuts.">
    <meta property="og:url" content="{SITE_URL}/cities/{slug}">
    <meta property="og:type" content="website">
    
    <!-- Favicon -->
    <link rel="icon" type="image/svg+xml" href="/favicon.svg">
    
    <script src="https://cdn.tailwindcss.com"></script>
    <link href="https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800&display=swap" rel="stylesheet">
    <style>
        body {{ font-family: 'Plus Jakarta Sans', sans-serif; }}
    </style>
    
    <!-- Local Business Schema -->
    <script type="application/ld+json">
    {{
        "@context": "https://schema.org",
        "@type": "WebPage",
        "name": "Great Clips Coupons {name}",
        "description": "Find Great Clips coupons and deals in {name}, {state}",
        "url": "{SITE_URL}/cities/{slug}",
        "mainEntity": {{
            "@type": "LocalBusiness",
            "name": "Great Clips {name}",
            "description": "Great Clips hair salon locations in {name}, {state}",
            "address": {{
                "@type": "PostalAddress",
                "addressLocality": "{name}",
                "addressRegion": "{state_abbr}"
            }},
            "priceRange": "$"
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
                    <img src="https://raw.githubusercontent.com/pineapplestocks/greatclips-coupons/main/docs/logo.png" alt="GreatClipsDeal" class="h-8 w-8 rounded-full object-cover">
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
            <a href="/states" class="hover:text-purple-600">States</a>
            <span class="mx-2">›</span>
            <a href="/{state_slug}" class="hover:text-purple-600">{state}</a>
            <span class="mx-2">›</span>
            <span class="text-slate-900">{name}</span>
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
                Great Clips Coupons {name}
            </h1>
            <p class="text-xl text-white/80 max-w-2xl mx-auto">
                {locations} locations in {name}, {state} • Save $5-$10 on haircuts
            </p>
        </div>
    </header>

    <!-- Main Content -->
    <main class="max-w-6xl mx-auto px-4 py-10">
        <!-- Stats Grid -->
        <section class="grid grid-cols-1 md:grid-cols-3 gap-6 mb-10">
            <div class="bg-white rounded-xl p-6 text-center shadow-sm">
                <div class="text-4xl font-bold text-purple-600 mb-2">$5.99</div>
                <div class="text-slate-600">Lowest Price</div>
            </div>
            <div class="bg-white rounded-xl p-6 text-center shadow-sm">
                <div class="text-4xl font-bold text-purple-600 mb-2">{locations}</div>
                <div class="text-slate-600">{name} Locations</div>
            </div>
            <div class="bg-white rounded-xl p-6 text-center shadow-sm">
                <div class="text-4xl font-bold text-purple-600 mb-2">Daily</div>
                <div class="text-slate-600">Coupon Updates</div>
            </div>
        </section>

        <!-- CTA Section -->
        <section class="bg-white rounded-2xl shadow-lg p-8 mb-10 text-center">
            <h2 class="text-2xl font-bold text-slate-900 mb-4">
                Get {name} Great Clips Coupons
            </h2>
            <p class="text-slate-600 mb-6 max-w-2xl mx-auto">
                Click below to see all available coupons for {name}, {state_abbr}. 
                Filter by location to find deals at your nearest Great Clips salon.
            </p>
            <a href="/?search={name.replace(' ', '+')}" class="inline-block bg-gradient-to-r from-violet-600 to-purple-600 hover:from-violet-700 hover:to-purple-700 text-white font-bold py-4 px-8 rounded-xl text-lg transition-all shadow-lg shadow-purple-200">
                View {name} Coupons →
            </a>
        </section>

        <!-- How to Use -->
        <section class="bg-white rounded-2xl shadow-sm p-8 mb-10">
            <h2 class="text-2xl font-bold text-slate-900 mb-6">
                How to Use Coupons in {name}
            </h2>
            <div class="grid md:grid-cols-2 gap-6">
                <div class="flex gap-4">
                    <div class="w-10 h-10 bg-purple-100 rounded-full flex items-center justify-center flex-shrink-0 font-bold text-purple-600">1</div>
                    <div>
                        <h3 class="font-semibold text-slate-900 mb-1">Find a Coupon</h3>
                        <p class="text-slate-600 text-sm">Browse coupons on our homepage and search for "{name}" to find local deals.</p>
                    </div>
                </div>
                <div class="flex gap-4">
                    <div class="w-10 h-10 bg-purple-100 rounded-full flex items-center justify-center flex-shrink-0 font-bold text-purple-600">2</div>
                    <div>
                        <h3 class="font-semibold text-slate-900 mb-1">Click to Reveal</h3>
                        <p class="text-slate-600 text-sm">Click "Get Coupon" to open the official offer. This starts the 14-day validity.</p>
                    </div>
                </div>
                <div class="flex gap-4">
                    <div class="w-10 h-10 bg-purple-100 rounded-full flex items-center justify-center flex-shrink-0 font-bold text-purple-600">3</div>
                    <div>
                        <h3 class="font-semibold text-slate-900 mb-1">Visit Great Clips</h3>
                        <p class="text-slate-600 text-sm">Go to any of the {locations} Great Clips locations in {name}.</p>
                    </div>
                </div>
                <div class="flex gap-4">
                    <div class="w-10 h-10 bg-purple-100 rounded-full flex items-center justify-center flex-shrink-0 font-bold text-purple-600">4</div>
                    <div>
                        <h3 class="font-semibold text-slate-900 mb-1">Show at Checkout</h3>
                        <p class="text-slate-600 text-sm">Show the coupon on your phone before paying to get your discount.</p>
                    </div>
                </div>
            </div>
        </section>

        <!-- About Section -->
        <section class="bg-white rounded-2xl shadow-sm p-8 mb-10">
            <h2 class="text-2xl font-bold text-slate-900 mb-4">
                About Great Clips in {name}
            </h2>
            <div class="text-slate-600 space-y-4">
                <p>
                    Great Clips has <strong>{locations} convenient locations</strong> throughout the {name} metropolitan area, 
                    making it easy to get an affordable, quality haircut near you. Whether you're in downtown {name} 
                    or the surrounding suburbs, there's a Great Clips salon ready to serve you.
                </p>
                <p>
                    With our daily-updated coupons, {name} residents can save <strong>$5 to $10 on every haircut</strong>. 
                    Most coupons offer prices between $5.99 and $8.99—well below the regular price of $15-$19.
                </p>
                <p>
                    Great Clips {name} locations offer walk-in service with no appointment needed. 
                    Use the Great Clips app to check in online and reduce your wait time.
                </p>
            </div>
        </section>

        <!-- Nearby Cities -->
        <section class="bg-white rounded-2xl shadow-sm p-8 mb-10">
            <h2 class="text-2xl font-bold text-slate-900 mb-6">
                Nearby Cities
            </h2>
            <div class="grid grid-cols-2 md:grid-cols-4 gap-4">
                {chr(10).join([f'<a href="/cities/{get_slug(c["name"])}" class="bg-slate-50 hover:bg-purple-50 rounded-lg p-4 text-center font-medium text-slate-700 hover:text-purple-600 transition-colors">{c["name"]}, {c["state_abbr"]}</a>' for c in nearby])}
                <a href="/{state_slug}" class="bg-purple-100 hover:bg-purple-200 rounded-lg p-4 text-center font-medium text-purple-700 transition-colors">All {state} →</a>
            </div>
        </section>

        <!-- FAQ Section -->
        <section class="bg-white rounded-2xl shadow-sm p-8">
            <h2 class="text-2xl font-bold text-slate-900 mb-6">
                {name} Great Clips FAQ
            </h2>
            <div class="space-y-6">
                <div>
                    <h3 class="font-semibold text-slate-900 mb-2">How many Great Clips are in {name}?</h3>
                    <p class="text-slate-600">There are {locations} Great Clips locations in the {name}, {state} metropolitan area. Use our search to find coupons for your nearest salon.</p>
                </div>
                <div>
                    <h3 class="font-semibold text-slate-900 mb-2">What's the cheapest Great Clips haircut in {name}?</h3>
                    <p class="text-slate-600">With our coupons, you can get a haircut for as low as $5.99 at participating {name} locations. Check our homepage for the current best deals.</p>
                </div>
                <div>
                    <h3 class="font-semibold text-slate-900 mb-2">Do {name} Great Clips accept all coupons?</h3>
                    <p class="text-slate-600">Most coupons work at all {name} locations, but some are specific to certain salons. Check the coupon details before visiting.</p>
                </div>
                <div>
                    <h3 class="font-semibold text-slate-900 mb-2">Does Great Clips in {name} offer senior discounts?</h3>
                    <p class="text-slate-600">Yes! Most {name} Great Clips locations offer senior discounts for customers 65+. <a href="/senior-discount" class="text-purple-600 hover:underline">Learn more about senior discounts</a>.</p>
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
                <p>© 2024-2026 GreatClipsDeal.com. Not affiliated with Great Clips Inc.</p>
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
    output_path.mkdir(parents=True, exist_ok=True)
    
    pages_generated = []
    
    for city in CITIES:
        html, slug = generate_city_page(city)
        filepath = output_path / f"{slug}.html"
        with open(filepath, 'w') as f:
            f.write(html)
        pages_generated.append(f"{SITE_URL}/cities/{slug}")
        print(f"✓ Generated {slug}.html")
    
    # Save list of generated URLs
    with open('generated_city_urls.txt', 'w') as f:
        f.write('\n'.join(pages_generated))
    
    print(f"\n✅ Generated {len(pages_generated)} city pages!")
    return pages_generated

if __name__ == "__main__":
    main()
