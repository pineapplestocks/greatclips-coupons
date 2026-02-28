#!/usr/bin/env python3
"""
Generate SEO-optimized state and city pages for GreatClipsDeal.com
"""

import os
from datetime import datetime

CURRENT_YEAR = "2026"
CURRENT_MONTH = "January"
CURRENT_DATE = datetime.now().strftime("%Y-%m-%d")

# State data with major cities
STATES = {
    'ohio': {'name': 'Ohio', 'code': 'OH', 'cities': ['Columbus', 'Cleveland', 'Cincinnati', 'Toledo', 'Akron'], 'locations': 280},
    'michigan': {'name': 'Michigan', 'code': 'MI', 'cities': ['Detroit', 'Grand Rapids', 'Warren', 'Lansing', 'Ann Arbor'], 'locations': 220},
    'pennsylvania': {'name': 'Pennsylvania', 'code': 'PA', 'cities': ['Philadelphia', 'Pittsburgh', 'Allentown', 'Erie', 'Reading'], 'locations': 180},
    'illinois': {'name': 'Illinois', 'code': 'IL', 'cities': ['Chicago', 'Aurora', 'Naperville', 'Joliet', 'Rockford'], 'locations': 200},
    'georgia': {'name': 'Georgia', 'code': 'GA', 'cities': ['Atlanta', 'Augusta', 'Savannah', 'Columbus', 'Macon'], 'locations': 150},
    'north-carolina': {'name': 'North Carolina', 'code': 'NC', 'cities': ['Charlotte', 'Raleigh', 'Greensboro', 'Durham', 'Winston-Salem'], 'locations': 160},
    'arizona': {'name': 'Arizona', 'code': 'AZ', 'cities': ['Phoenix', 'Tucson', 'Mesa', 'Chandler', 'Scottsdale'], 'locations': 130},
    'minnesota': {'name': 'Minnesota', 'code': 'MN', 'cities': ['Minneapolis', 'Saint Paul', 'Rochester', 'Bloomington', 'Duluth'], 'locations': 170},
    'indiana': {'name': 'Indiana', 'code': 'IN', 'cities': ['Indianapolis', 'Fort Wayne', 'Evansville', 'South Bend', 'Carmel'], 'locations': 140},
    'wisconsin': {'name': 'Wisconsin', 'code': 'WI', 'cities': ['Milwaukee', 'Madison', 'Green Bay', 'Kenosha', 'Racine'], 'locations': 150},
    'colorado': {'name': 'Colorado', 'code': 'CO', 'cities': ['Denver', 'Colorado Springs', 'Aurora', 'Fort Collins', 'Boulder'], 'locations': 120},
    'tennessee': {'name': 'Tennessee', 'code': 'TN', 'cities': ['Nashville', 'Memphis', 'Knoxville', 'Chattanooga', 'Clarksville'], 'locations': 130},
    'virginia': {'name': 'Virginia', 'code': 'VA', 'cities': ['Virginia Beach', 'Norfolk', 'Chesapeake', 'Richmond', 'Arlington'], 'locations': 140},
    'washington': {'name': 'Washington', 'code': 'WA', 'cities': ['Seattle', 'Spokane', 'Tacoma', 'Vancouver', 'Bellevue'], 'locations': 110},
    'new-york': {'name': 'New York', 'code': 'NY', 'cities': ['New York City', 'Buffalo', 'Rochester', 'Syracuse', 'Albany'], 'locations': 160},
}

# Major cities for dedicated pages
CITIES = {
    'houston': {'name': 'Houston', 'state': 'Texas', 'state_code': 'TX', 'locations': 45},
    'dallas': {'name': 'Dallas', 'state': 'Texas', 'state_code': 'TX', 'locations': 38},
    'chicago': {'name': 'Chicago', 'state': 'Illinois', 'state_code': 'IL', 'locations': 42},
    'phoenix': {'name': 'Phoenix', 'state': 'Arizona', 'state_code': 'AZ', 'locations': 35},
    'columbus': {'name': 'Columbus', 'state': 'Ohio', 'state_code': 'OH', 'locations': 28},
    'atlanta': {'name': 'Atlanta', 'state': 'Georgia', 'state_code': 'GA', 'locations': 32},
    'denver': {'name': 'Denver', 'state': 'Colorado', 'state_code': 'CO', 'locations': 25},
    'minneapolis': {'name': 'Minneapolis', 'state': 'Minnesota', 'state_code': 'MN', 'locations': 30},
    'detroit': {'name': 'Detroit', 'state': 'Michigan', 'state_code': 'MI', 'locations': 28},
    'indianapolis': {'name': 'Indianapolis', 'state': 'Indiana', 'state_code': 'IN', 'locations': 22},
}

def generate_state_page(slug, data):
    """Generate a state page"""
    name = data['name']
    code = data['code']
    cities = data['cities']
    locations = data['locations']
    cities_list = ', '.join(cities[:4])
    
    return f'''<!DOCTYPE html>
<html lang="en">
<head>
    <!-- Google tag (gtag.js) -->
    <script async src="https://www.googletagmanager.com/gtag/js?id=G-90ZQ7M4EFR"></script>
    <script>
      window.dataLayer = window.dataLayer || [];
      function gtag(){{dataLayer.push(arguments);}}
      gtag('js', new Date());
      gtag('config', 'G-90ZQ7M4EFR');
    </script>
    
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    
    <title>Great Clips Coupons {name} ({CURRENT_MONTH} {CURRENT_YEAR}) - ${code} Haircut Deals</title>
    <meta name="description" content="Find Great Clips coupons for {name}. Save $5-$10 on haircuts at {locations}+ {code} locations including {cities_list}. Updated daily with $5.99-$8.99 deals.">
    <meta name="keywords" content="Great Clips coupons {name}, Great Clips {code}, Great Clips coupon {cities[0]}, {name} haircut coupons, cheap haircuts {name}">
    <link rel="canonical" href="https://greatclipsdeal.com/{slug}">
    
    <!-- Open Graph -->
    <meta property="og:type" content="website">
    <meta property="og:url" content="https://greatclipsdeal.com/{slug}">
    <meta property="og:title" content="Great Clips Coupons {name} - $5.99+ Haircut Deals">
    <meta property="og:description" content="Find Great Clips coupons for {name}. Daily updated deals at {locations}+ locations.">
    <meta property="og:image" content="https://greatclipsdeal.com/icon-512.png">
    
    <!-- Schema: WebPage with geo targeting -->
    <script type="application/ld+json">
    {{
        "@context": "https://schema.org",
        "@type": "WebPage",
        "name": "Great Clips Coupons in {name} - {CURRENT_MONTH} {CURRENT_YEAR}",
        "description": "Find Great Clips haircut coupons for {name}. Daily updated deals from $5.99-$8.99 at {name} Great Clips locations.",
        "url": "https://greatclipsdeal.com/{slug}",
        "dateModified": "{CURRENT_DATE}",
        "about": {{
            "@type": "Place",
            "name": "{name}",
            "address": {{
                "@type": "PostalAddress",
                "addressRegion": "{code}",
                "addressCountry": "US"
            }}
        }}
    }}
    </script>
    
    <!-- Schema: BreadcrumbList -->
    <script type="application/ld+json">
    {{
        "@context": "https://schema.org",
        "@type": "BreadcrumbList",
        "itemListElement": [
            {{"@type": "ListItem", "position": 1, "name": "Home", "item": "https://greatclipsdeal.com/"}},
            {{"@type": "ListItem", "position": 2, "name": "States", "item": "https://greatclipsdeal.com/states"}},
            {{"@type": "ListItem", "position": 3, "name": "{name}", "item": "https://greatclipsdeal.com/{slug}"}}
        ]
    }}
    </script>
    
    <!-- Schema: FAQPage -->
    <script type="application/ld+json">
    {{
        "@context": "https://schema.org",
        "@type": "FAQPage",
        "mainEntity": [
            {{
                "@type": "Question",
                "name": "How much does a Great Clips haircut cost in {name}?",
                "acceptedAnswer": {{
                    "@type": "Answer",
                    "text": "Great Clips haircuts in {name} typically cost $15-19 without a coupon. With coupons from greatclipsdeal.com, {name} customers can pay as little as $5.99-$8.99."
                }}
            }},
            {{
                "@type": "Question",
                "name": "Where can I find Great Clips coupons for {name}?",
                "acceptedAnswer": {{
                    "@type": "Answer",
                    "text": "GreatClipsDeal.com has daily updated coupons that work at {name} Great Clips locations. We pull coupons from official Great Clips Facebook ads. Filter by {code} to see {name} deals."
                }}
            }},
            {{
                "@type": "Question",
                "name": "How many Great Clips are in {name}?",
                "acceptedAnswer": {{
                    "@type": "Answer",
                    "text": "There are approximately {locations}+ Great Clips locations in {name}, with salons in {cities_list}, and many other cities across the state."
                }}
            }}
        ]
    }}
    </script>

    <script src="https://cdn.tailwindcss.com"></script>
    <style>
        .gradient-bg {{ background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); }}
    </style>
</head>
<body class="bg-slate-50 min-h-screen">
    <header class="gradient-bg text-white py-16">
        <div class="max-w-4xl mx-auto px-4 text-center">
            <nav class="mb-8">
                <a href="/" class="text-white/80 hover:text-white">← All Coupons</a>
                <span class="mx-2 text-white/50">|</span>
                <a href="/states" class="text-white/80 hover:text-white">All States</a>
            </nav>
            <span class="bg-green-500 text-white text-sm font-bold px-4 py-1 rounded-full mb-4 inline-block">UPDATED {CURRENT_MONTH.upper()} {CURRENT_YEAR}</span>
            <h1 class="text-4xl md:text-5xl font-extrabold mb-4">Great Clips Coupons {name}</h1>
            <p class="text-xl text-white/80 mb-2">{locations}+ locations • {cities_list} & more</p>
            <p class="text-white/60">Save $5-$10 on your next haircut in {name}</p>
        </div>
    </header>

    <main class="max-w-4xl mx-auto px-4 py-12">
        <!-- Quick Stats -->
        <div class="grid md:grid-cols-3 gap-6 mb-12">
            <div class="bg-white rounded-xl p-6 shadow-md text-center">
                <div class="text-3xl font-bold text-green-600">$5.99</div>
                <p class="text-slate-600">Lowest Price</p>
            </div>
            <div class="bg-white rounded-xl p-6 shadow-md text-center">
                <div class="text-3xl font-bold text-purple-600">{locations}+</div>
                <p class="text-slate-600">{name} Locations</p>
            </div>
            <div class="bg-white rounded-xl p-6 shadow-md text-center">
                <div class="text-3xl font-bold text-blue-600">Daily</div>
                <p class="text-slate-600">Updates</p>
            </div>
        </div>

        <!-- CTA -->
        <div class="bg-gradient-to-r from-green-500 to-emerald-500 rounded-2xl p-8 text-white text-center mb-12">
            <h2 class="text-2xl font-bold mb-4">Get {name} Great Clips Coupons</h2>
            <p class="mb-6 text-white/90">Click below to see all available coupons for {code}</p>
            <a href="/?state={code}" class="inline-block bg-white text-green-600 font-bold py-3 px-8 rounded-xl hover:bg-green-50 transition-all">
                View {name} Coupons →
            </a>
        </div>

        <!-- Cities Section -->
        <div class="bg-white rounded-xl p-8 shadow-md mb-12">
            <h2 class="text-2xl font-bold text-slate-900 mb-6">Great Clips in {name} Cities</h2>
            <div class="grid md:grid-cols-2 gap-4">
                {"".join(f'<div class="flex items-center gap-2"><span class="text-green-500">✓</span> {city}</div>' for city in cities)}
            </div>
            <p class="mt-6 text-slate-600">Coupons work at most {name} locations. Filter by city on our main page.</p>
        </div>

        <!-- How to Use -->
        <div class="bg-white rounded-xl p-8 shadow-md mb-12">
            <h2 class="text-2xl font-bold text-slate-900 mb-6">How to Use Coupons in {name}</h2>
            <ol class="space-y-4">
                <li class="flex gap-4">
                    <span class="bg-purple-100 text-purple-600 font-bold w-8 h-8 rounded-full flex items-center justify-center flex-shrink-0">1</span>
                    <div><strong>Find a coupon</strong> - Browse coupons on our homepage and filter by {code}</div>
                </li>
                <li class="flex gap-4">
                    <span class="bg-purple-100 text-purple-600 font-bold w-8 h-8 rounded-full flex items-center justify-center flex-shrink-0">2</span>
                    <div><strong>Click to reveal</strong> - Open the coupon to start the 14-day validity period</div>
                </li>
                <li class="flex gap-4">
                    <span class="bg-purple-100 text-purple-600 font-bold w-8 h-8 rounded-full flex items-center justify-center flex-shrink-0">3</span>
                    <div><strong>Visit Great Clips</strong> - Go to any {name} location</div>
                </li>
                <li class="flex gap-4">
                    <span class="bg-purple-100 text-purple-600 font-bold w-8 h-8 rounded-full flex items-center justify-center flex-shrink-0">4</span>
                    <div><strong>Show at checkout</strong> - Display coupon on your phone to get discount</div>
                </li>
            </ol>
        </div>

        <!-- FAQ -->
        <div class="bg-white rounded-xl p-8 shadow-md mb-12">
            <h2 class="text-2xl font-bold text-slate-900 mb-6">{name} Great Clips FAQ</h2>
            <div class="space-y-6">
                <div>
                    <h3 class="font-bold text-slate-900 mb-2">How much does a Great Clips haircut cost in {name}?</h3>
                    <p class="text-slate-600">Without a coupon, expect to pay $15-19 for an adult haircut. With our coupons, you can pay as little as $5.99-$8.99.</p>
                </div>
                <div>
                    <h3 class="font-bold text-slate-900 mb-2">Do coupons work at all {name} Great Clips?</h3>
                    <p class="text-slate-600">Most coupons work at all {locations}+ {name} locations. Some may be specific to certain cities - check the coupon details.</p>
                </div>
                <div>
                    <h3 class="font-bold text-slate-900 mb-2">How often are {name} coupons updated?</h3>
                    <p class="text-slate-600">We update coupons daily by scanning official Great Clips Facebook ads. Check back regularly for new deals.</p>
                </div>
            </div>
        </div>

        <!-- Other States -->
        <div class="bg-slate-100 rounded-xl p-8">
            <h2 class="text-xl font-bold text-slate-900 mb-4">Coupons for Other States</h2>
            <div class="flex flex-wrap gap-2">
                <a href="/texas" class="bg-white px-4 py-2 rounded-lg hover:bg-purple-50 transition-colors">Texas</a>
                <a href="/california" class="bg-white px-4 py-2 rounded-lg hover:bg-purple-50 transition-colors">California</a>
                <a href="/florida" class="bg-white px-4 py-2 rounded-lg hover:bg-purple-50 transition-colors">Florida</a>
                <a href="/ohio" class="bg-white px-4 py-2 rounded-lg hover:bg-purple-50 transition-colors">Ohio</a>
                <a href="/states" class="bg-purple-600 text-white px-4 py-2 rounded-lg hover:bg-purple-700 transition-colors">All States →</a>
            </div>
        </div>
    </main>

    <footer class="bg-slate-900 text-white py-12 mt-12">
        <div class="max-w-4xl mx-auto px-4 text-center">
            <p class="text-slate-400 mb-4">Updated daily with official Great Clips coupons</p>
            <a href="/" class="text-purple-400 hover:text-purple-300">GreatClipsDeal.com</a>
        </div>
    </footer>
</body>
</html>'''


def generate_city_page(slug, data):
    """Generate a city page"""
    name = data['name']
    state = data['state']
    state_code = data['state_code']
    locations = data['locations']
    
    return f'''<!DOCTYPE html>
<html lang="en">
<head>
    <!-- Google tag (gtag.js) -->
    <script async src="https://www.googletagmanager.com/gtag/js?id=G-90ZQ7M4EFR"></script>
    <script>
      window.dataLayer = window.dataLayer || [];
      function gtag(){{dataLayer.push(arguments);}}
      gtag('js', new Date());
      gtag('config', 'G-90ZQ7M4EFR');
    </script>
    
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    
    <title>Great Clips Coupons {name}, {state_code} ({CURRENT_MONTH} {CURRENT_YEAR}) - Local Deals</title>
    <meta name="description" content="Find Great Clips coupons for {name}, {state}. Save $5-$10 on haircuts at {locations}+ {name} area locations. Updated daily with $5.99-$8.99 deals.">
    <meta name="keywords" content="Great Clips coupons {name}, Great Clips {name} {state_code}, {name} haircut coupons, cheap haircuts {name}">
    <link rel="canonical" href="https://greatclipsdeal.com/{slug}">
    
    <!-- Open Graph -->
    <meta property="og:type" content="website">
    <meta property="og:url" content="https://greatclipsdeal.com/{slug}">
    <meta property="og:title" content="Great Clips Coupons {name} - $5.99+ Haircut Deals">
    <meta property="og:description" content="Find Great Clips coupons for {name}, {state}. Daily updated deals.">
    <meta property="og:image" content="https://greatclipsdeal.com/icon-512.png">
    
    <!-- Schema: LocalBusiness -->
    <script type="application/ld+json">
    {{
        "@context": "https://schema.org",
        "@type": "WebPage",
        "name": "Great Clips Coupons in {name}, {state_code}",
        "description": "Find Great Clips haircut coupons for {name}, {state}. Daily updated deals from $5.99-$8.99.",
        "url": "https://greatclipsdeal.com/{slug}",
        "dateModified": "{CURRENT_DATE}",
        "about": {{
            "@type": "Place",
            "name": "{name}",
            "address": {{
                "@type": "PostalAddress",
                "addressLocality": "{name}",
                "addressRegion": "{state_code}",
                "addressCountry": "US"
            }}
        }}
    }}
    </script>
    
    <!-- Schema: BreadcrumbList -->
    <script type="application/ld+json">
    {{
        "@context": "https://schema.org",
        "@type": "BreadcrumbList",
        "itemListElement": [
            {{"@type": "ListItem", "position": 1, "name": "Home", "item": "https://greatclipsdeal.com/"}},
            {{"@type": "ListItem", "position": 2, "name": "{state}", "item": "https://greatclipsdeal.com/{state.lower().replace(' ', '-')}"}},
            {{"@type": "ListItem", "position": 3, "name": "{name}", "item": "https://greatclipsdeal.com/{slug}"}}
        ]
    }}
    </script>
    
    <!-- Schema: FAQPage -->
    <script type="application/ld+json">
    {{
        "@context": "https://schema.org",
        "@type": "FAQPage",
        "mainEntity": [
            {{
                "@type": "Question",
                "name": "How much is a Great Clips haircut in {name}?",
                "acceptedAnswer": {{
                    "@type": "Answer",
                    "text": "Great Clips haircuts in {name} typically cost $15-19 without a coupon. With coupons from greatclipsdeal.com, you can pay as little as $5.99-$8.99 at {name} area locations."
                }}
            }},
            {{
                "@type": "Question",
                "name": "How many Great Clips are in {name}?",
                "acceptedAnswer": {{
                    "@type": "Answer",
                    "text": "There are approximately {locations}+ Great Clips locations in the {name} metro area. Use our coupons at any of these locations."
                }}
            }}
        ]
    }}
    </script>

    <script src="https://cdn.tailwindcss.com"></script>
    <style>
        .gradient-bg {{ background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); }}
    </style>
</head>
<body class="bg-slate-50 min-h-screen">
    <header class="gradient-bg text-white py-16">
        <div class="max-w-4xl mx-auto px-4 text-center">
            <nav class="mb-8">
                <a href="/" class="text-white/80 hover:text-white">← All Coupons</a>
                <span class="mx-2 text-white/50">|</span>
                <a href="/{state.lower().replace(' ', '-')}" class="text-white/80 hover:text-white">{state}</a>
            </nav>
            <span class="bg-green-500 text-white text-sm font-bold px-4 py-1 rounded-full mb-4 inline-block">UPDATED {CURRENT_MONTH.upper()} {CURRENT_YEAR}</span>
            <h1 class="text-4xl md:text-5xl font-extrabold mb-4">Great Clips Coupons {name}</h1>
            <p class="text-xl text-white/80 mb-2">{locations}+ locations in {name}, {state_code}</p>
            <p class="text-white/60">Save $5-$10 on your next haircut</p>
        </div>
    </header>

    <main class="max-w-4xl mx-auto px-4 py-12">
        <!-- Quick Stats -->
        <div class="grid md:grid-cols-3 gap-6 mb-12">
            <div class="bg-white rounded-xl p-6 shadow-md text-center">
                <div class="text-3xl font-bold text-green-600">$5.99</div>
                <p class="text-slate-600">Lowest Price</p>
            </div>
            <div class="bg-white rounded-xl p-6 shadow-md text-center">
                <div class="text-3xl font-bold text-purple-600">{locations}+</div>
                <p class="text-slate-600">{name} Locations</p>
            </div>
            <div class="bg-white rounded-xl p-6 shadow-md text-center">
                <div class="text-3xl font-bold text-blue-600">Daily</div>
                <p class="text-slate-600">Updates</p>
            </div>
        </div>

        <!-- CTA -->
        <div class="bg-gradient-to-r from-green-500 to-emerald-500 rounded-2xl p-8 text-white text-center mb-12">
            <h2 class="text-2xl font-bold mb-4">Get {name} Great Clips Coupons</h2>
            <p class="mb-6 text-white/90">Click below to see all available coupons</p>
            <a href="/?search={name}" class="inline-block bg-white text-green-600 font-bold py-3 px-8 rounded-xl hover:bg-green-50 transition-all">
                View {name} Coupons →
            </a>
        </div>

        <!-- Info -->
        <div class="bg-white rounded-xl p-8 shadow-md mb-12">
            <h2 class="text-2xl font-bold text-slate-900 mb-6">Great Clips in {name}, {state}</h2>
            <p class="text-slate-600 mb-4">
                {name} has {locations}+ Great Clips locations throughout the metro area. Whether you're downtown, 
                in the suburbs, or anywhere in between, there's a Great Clips near you.
            </p>
            <p class="text-slate-600 mb-4">
                Our coupons are pulled from official Great Clips Facebook ads and work at most {name} locations. 
                Prices typically range from <strong>$5.99 to $8.99</strong> with a coupon, compared to $15-19 regular price.
            </p>
            <p class="text-slate-600">
                <strong>Pro tip:</strong> Use the Great Clips app to check wait times at {name} locations before you go!
            </p>
        </div>

        <!-- FAQ -->
        <div class="bg-white rounded-xl p-8 shadow-md mb-12">
            <h2 class="text-2xl font-bold text-slate-900 mb-6">{name} Great Clips FAQ</h2>
            <div class="space-y-6">
                <div>
                    <h3 class="font-bold text-slate-900 mb-2">What's the cheapest Great Clips haircut in {name}?</h3>
                    <p class="text-slate-600">With our coupons, you can get haircuts for as low as $5.99 at {name} Great Clips locations.</p>
                </div>
                <div>
                    <h3 class="font-bold text-slate-900 mb-2">Do I need an appointment at Great Clips {name}?</h3>
                    <p class="text-slate-600">No! Great Clips is walk-in friendly. You can also check in online via their app to save time.</p>
                </div>
            </div>
        </div>

        <!-- Related -->
        <div class="bg-slate-100 rounded-xl p-8">
            <h2 class="text-xl font-bold text-slate-900 mb-4">More {state} Coupons</h2>
            <div class="flex flex-wrap gap-2">
                <a href="/{state.lower().replace(' ', '-')}" class="bg-white px-4 py-2 rounded-lg hover:bg-purple-50 transition-colors">All {state}</a>
                <a href="/states" class="bg-purple-600 text-white px-4 py-2 rounded-lg hover:bg-purple-700 transition-colors">All States →</a>
            </div>
        </div>
    </main>

    <footer class="bg-slate-900 text-white py-12 mt-12">
        <div class="max-w-4xl mx-auto px-4 text-center">
            <p class="text-slate-400 mb-4">Updated daily with official Great Clips coupons</p>
            <a href="/" class="text-purple-400 hover:text-purple-300">GreatClipsDeal.com</a>
        </div>
    </footer>
</body>
</html>'''


def main():
    os.makedirs('pages', exist_ok=True)
    os.makedirs('pages/cities', exist_ok=True)
    
    print("Generating State Pages...")
    for slug, data in STATES.items():
        filepath = f'pages/{slug}.html'
        with open(filepath, 'w') as f:
            f.write(generate_state_page(slug, data))
        print(f"  Created: {filepath}")
    
    print("\nGenerating City Pages...")
    for slug, data in CITIES.items():
        filepath = f'pages/cities/{slug}.html'
        with open(filepath, 'w') as f:
            f.write(generate_city_page(slug, data))
        print(f"  Created: {filepath}")
    
    print(f"\n✅ Created {len(STATES)} state pages and {len(CITIES)} city pages!")

if __name__ == "__main__":
    main()
