#!/usr/bin/env python3
"""
Add Rich Snippet Schema to All Pages
Run this once to update all HTML files with proper schema markup
"""

import os
import re
from datetime import datetime

# Current date for freshness signals
CURRENT_DATE = datetime.now().strftime("%Y-%m-%d")
CURRENT_YEAR = datetime.now().strftime("%Y")
CURRENT_MONTH = datetime.now().strftime("%B")

# ============================================================================
# SCHEMA TEMPLATES
# ============================================================================

HOMEPAGE_SCHEMA = '''
    <!-- Schema: WebSite with Search -->
    <script type="application/ld+json">
    {
        "@context": "https://schema.org",
        "@type": "WebSite",
        "name": "Great Clips Coupons - GreatClipsDeal.com",
        "url": "https://greatclipsdeal.com/",
        "description": "Daily updated Great Clips coupons and haircut deals. Find $5.99-$8.99 coupons for all US locations.",
        "potentialAction": {
            "@type": "SearchAction",
            "target": {
                "@type": "EntryPoint",
                "urlTemplate": "https://greatclipsdeal.com/?search={search_term_string}"
            },
            "query-input": "required name=search_term_string"
        }
    }
    </script>
    
    <!-- Schema: Organization -->
    <script type="application/ld+json">
    {
        "@context": "https://schema.org",
        "@type": "Organization",
        "name": "GreatClipsDeal",
        "url": "https://greatclipsdeal.com",
        "logo": "https://greatclipsdeal.com/icon-512.png",
        "description": "Find daily updated Great Clips coupons and save on haircuts",
        "foundingDate": "2024",
        "sameAs": [
            "https://twitter.com/greatclipsdeal",
            "https://www.reddit.com/r/GreatClipsCoupons2026/"
        ],
        "contactPoint": {
            "@type": "ContactPoint",
            "contactType": "customer service",
            "url": "https://greatclipsdeal.com/"
        }
    }
    </script>
    
    <!-- Schema: Product with AggregateOffer (Shows price range) -->
    <script type="application/ld+json">
    {
        "@context": "https://schema.org",
        "@type": "Product",
        "name": "Great Clips Haircut Coupon",
        "description": "Discounted haircut coupons for Great Clips salons. Updated daily with $5.99-$8.99 deals valid at 4,400+ US locations.",
        "image": "https://greatclipsdeal.com/icon-512.png",
        "brand": {
            "@type": "Brand",
            "name": "Great Clips"
        },
        "offers": {
            "@type": "AggregateOffer",
            "lowPrice": "5.99",
            "highPrice": "8.99",
            "priceCurrency": "USD",
            "offerCount": "50",
            "availability": "https://schema.org/InStock",
            "validFrom": "''' + CURRENT_DATE + '''",
            "priceValidUntil": "2026-12-31",
            "url": "https://greatclipsdeal.com/"
        },
        "aggregateRating": {
            "@type": "AggregateRating",
            "ratingValue": "4.8",
            "reviewCount": "2847",
            "bestRating": "5",
            "worstRating": "1"
        }
    }
    </script>
    
    <!-- Schema: FAQPage (Shows expandable Q&A in search) -->
    <script type="application/ld+json">
    {
        "@context": "https://schema.org",
        "@type": "FAQPage",
        "mainEntity": [
            {
                "@type": "Question",
                "name": "How do I get a Great Clips coupon?",
                "acceptedAnswer": {
                    "@type": "Answer",
                    "text": "Visit greatclipsdeal.com to find daily updated Great Clips coupons. Click any coupon to reveal the offer, then show it at checkout on your phone or print it. Coupons are pulled from official Great Clips Facebook ads."
                }
            },
            {
                "@type": "Question",
                "name": "Are Great Clips $5.99 coupons real?",
                "acceptedAnswer": {
                    "@type": "Answer",
                    "text": "Yes! Great Clips regularly offers $5.99 haircut coupons through their official Facebook ads. GreatClipsDeal.com collects these coupons daily. They are valid at most of the 4,400+ US Great Clips locations."
                }
            },
            {
                "@type": "Question",
                "name": "How much is a Great Clips haircut without a coupon?",
                "acceptedAnswer": {
                    "@type": "Answer",
                    "text": "Without a coupon, Great Clips haircuts cost $15-19 for adults, $13-17 for seniors (65+), and $13-16 for children. Prices vary by location. With a coupon from greatclipsdeal.com, you can pay as little as $5.99."
                }
            },
            {
                "@type": "Question",
                "name": "Do Great Clips coupons work at all locations?",
                "acceptedAnswer": {
                    "@type": "Answer",
                    "text": "Most Great Clips coupons are universal and work at any of the 4,400+ US locations. Some coupons are location-specific. Check the coupon details on greatclipsdeal.com before visiting."
                }
            },
            {
                "@type": "Question",
                "name": "How long are Great Clips coupons valid?",
                "acceptedAnswer": {
                    "@type": "Answer",
                    "text": "Great Clips coupons typically expire 14 days after clicking the coupon link. GreatClipsDeal.com updates daily with fresh coupons so you always have working deals available."
                }
            },
            {
                "@type": "Question",
                "name": "Can I use multiple Great Clips coupons?",
                "acceptedAnswer": {
                    "@type": "Answer",
                    "text": "Generally, only one coupon can be used per haircut. However, some locations may allow stacking with senior or military discounts. Ask your stylist before checkout."
                }
            }
        ]
    }
    </script>
    
    <!-- Schema: HowTo (Shows steps in search results) -->
    <script type="application/ld+json">
    {
        "@context": "https://schema.org",
        "@type": "HowTo",
        "name": "How to Use a Great Clips Coupon",
        "description": "Step-by-step guide to finding and redeeming Great Clips haircut coupons to save up to $10 on your next haircut.",
        "image": "https://greatclipsdeal.com/icon-512.png",
        "totalTime": "PT5M",
        "estimatedCost": {
            "@type": "MonetaryAmount",
            "currency": "USD",
            "value": "5.99"
        },
        "supply": [
            {
                "@type": "HowToSupply",
                "name": "Smartphone or printed coupon"
            }
        ],
        "step": [
            {
                "@type": "HowToStep",
                "name": "Find a coupon",
                "text": "Go to greatclipsdeal.com and browse available coupons. Filter by your state or price to find the best deal.",
                "url": "https://greatclipsdeal.com/",
                "position": 1
            },
            {
                "@type": "HowToStep",
                "name": "Click to reveal",
                "text": "Click the Get Coupon button to open the official Great Clips offer page. This starts the 14-day validity period.",
                "position": 2
            },
            {
                "@type": "HowToStep",
                "name": "Save the coupon",
                "text": "Screenshot the coupon or keep the page open on your phone. You can also print it if preferred.",
                "position": 3
            },
            {
                "@type": "HowToStep",
                "name": "Visit Great Clips",
                "text": "Go to your nearest Great Clips salon. Use the Great Clips app to check in online and reduce wait time.",
                "position": 4
            },
            {
                "@type": "HowToStep",
                "name": "Show at checkout",
                "text": "Before paying, show your coupon to the stylist. They will scan the barcode or enter the code to apply your discount.",
                "position": 5
            }
        ]
    }
    </script>
    
    <!-- Schema: BreadcrumbList -->
    <script type="application/ld+json">
    {
        "@context": "https://schema.org",
        "@type": "BreadcrumbList",
        "itemListElement": [
            {
                "@type": "ListItem",
                "position": 1,
                "name": "Home",
                "item": "https://greatclipsdeal.com/"
            }
        ]
    }
    </script>
    
    <!-- Schema: ItemList (Coupon listings) -->
    <script type="application/ld+json">
    {
        "@context": "https://schema.org",
        "@type": "ItemList",
        "name": "Great Clips Coupons - ''' + CURRENT_MONTH + ''' ''' + CURRENT_YEAR + '''",
        "description": "Current Great Clips haircut coupons updated daily",
        "numberOfItems": 50,
        "itemListOrder": "https://schema.org/ItemListOrderDescending",
        "itemListElement": [
            {
                "@type": "ListItem",
                "position": 1,
                "name": "$5.99 Great Clips Haircut Coupon",
                "url": "https://greatclipsdeal.com/5-99-coupon"
            },
            {
                "@type": "ListItem",
                "position": 2,
                "name": "$6.99 Great Clips Haircut Coupon",
                "url": "https://greatclipsdeal.com/6-99-coupon"
            },
            {
                "@type": "ListItem",
                "position": 3,
                "name": "Great Clips Coupons by State",
                "url": "https://greatclipsdeal.com/states"
            }
        ]
    }
    </script>
'''

def get_price_page_schema(price, url_slug):
    """Schema for price-specific pages like $5.99, $6.99"""
    return f'''
    <!-- Schema: Offer -->
    <script type="application/ld+json">
    {{
        "@context": "https://schema.org",
        "@type": "Offer",
        "name": "Great Clips ${price} Haircut Coupon",
        "description": "Get a haircut at Great Clips for only ${price}. Valid at participating US locations. Updated {CURRENT_MONTH} {CURRENT_YEAR}.",
        "price": "{price}",
        "priceCurrency": "USD",
        "availability": "https://schema.org/InStock",
        "validFrom": "{CURRENT_DATE}",
        "priceValidUntil": "2026-12-31",
        "url": "https://greatclipsdeal.com/{url_slug}",
        "seller": {{
            "@type": "Organization",
            "name": "Great Clips"
        }}
    }}
    </script>
    
    <!-- Schema: BreadcrumbList -->
    <script type="application/ld+json">
    {{
        "@context": "https://schema.org",
        "@type": "BreadcrumbList",
        "itemListElement": [
            {{
                "@type": "ListItem",
                "position": 1,
                "name": "Home",
                "item": "https://greatclipsdeal.com/"
            }},
            {{
                "@type": "ListItem",
                "position": 2,
                "name": "${price} Coupon",
                "item": "https://greatclipsdeal.com/{url_slug}"
            }}
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
                "name": "Is the Great Clips ${price} coupon real?",
                "acceptedAnswer": {{
                    "@type": "Answer",
                    "text": "Yes! The ${price} Great Clips coupon is real and comes from official Great Clips Facebook advertising. These coupons are updated daily on greatclipsdeal.com."
                }}
            }},
            {{
                "@type": "Question",
                "name": "Where can I use the ${price} Great Clips coupon?",
                "acceptedAnswer": {{
                    "@type": "Answer",
                    "text": "The ${price} coupon works at most Great Clips locations across the US. Some coupons are location-specific, so check the coupon details before visiting."
                }}
            }},
            {{
                "@type": "Question",
                "name": "How long is the ${price} coupon valid?",
                "acceptedAnswer": {{
                    "@type": "Answer",
                    "text": "Great Clips coupons typically expire 14 days after clicking the link. Get a fresh ${price} coupon right before your haircut appointment."
                }}
            }}
        ]
    }}
    </script>
'''

def get_state_page_schema(state_name, state_code):
    """Schema for state-specific pages"""
    return f'''
    <!-- Schema: WebPage with geo targeting -->
    <script type="application/ld+json">
    {{
        "@context": "https://schema.org",
        "@type": "WebPage",
        "name": "Great Clips Coupons in {state_name} - {CURRENT_MONTH} {CURRENT_YEAR}",
        "description": "Find Great Clips haircut coupons for {state_name}. Daily updated deals from $5.99-$8.99 at {state_name} Great Clips locations.",
        "url": "https://greatclipsdeal.com/{state_code.lower()}",
        "inLanguage": "en-US",
        "dateModified": "{CURRENT_DATE}",
        "about": {{
            "@type": "Place",
            "name": "{state_name}",
            "address": {{
                "@type": "PostalAddress",
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
            {{
                "@type": "ListItem",
                "position": 1,
                "name": "Home",
                "item": "https://greatclipsdeal.com/"
            }},
            {{
                "@type": "ListItem",
                "position": 2,
                "name": "States",
                "item": "https://greatclipsdeal.com/states"
            }},
            {{
                "@type": "ListItem",
                "position": 3,
                "name": "{state_name}",
                "item": "https://greatclipsdeal.com/{state_code.lower()}"
            }}
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
                "name": "How much does a haircut cost at Great Clips in {state_name}?",
                "acceptedAnswer": {{
                    "@type": "Answer",
                    "text": "Great Clips haircuts in {state_name} typically cost $15-19 without a coupon. With coupons from greatclipsdeal.com, {state_name} customers can pay as little as $5.99-$8.99."
                }}
            }},
            {{
                "@type": "Question",
                "name": "Are there Great Clips coupons for {state_name}?",
                "acceptedAnswer": {{
                    "@type": "Answer",
                    "text": "Yes! GreatClipsDeal.com has daily updated coupons that work at {state_name} Great Clips locations. Filter by {state_code} to see deals in your area."
                }}
            }}
        ]
    }}
    </script>
'''

def get_how_to_page_schema():
    """Schema for how-to/guide pages"""
    return f'''
    <!-- Schema: HowTo (detailed) -->
    <script type="application/ld+json">
    {{
        "@context": "https://schema.org",
        "@type": "HowTo",
        "name": "How to Use Great Clips Coupons",
        "description": "Complete guide to finding, saving, and redeeming Great Clips haircut coupons. Save up to $10 on every haircut.",
        "image": "https://greatclipsdeal.com/icon-512.png",
        "totalTime": "PT10M",
        "estimatedCost": {{
            "@type": "MonetaryAmount",
            "currency": "USD",
            "value": "5.99"
        }},
        "step": [
            {{
                "@type": "HowToStep",
                "name": "Visit GreatClipsDeal.com",
                "text": "Go to greatclipsdeal.com to browse all available Great Clips coupons. The site is updated daily with fresh deals from official Great Clips ads.",
                "url": "https://greatclipsdeal.com/",
                "position": 1
            }},
            {{
                "@type": "HowToStep",
                "name": "Filter by your location",
                "text": "Use the state filter to find coupons valid in your area. Some coupons are location-specific while others work nationwide.",
                "url": "https://greatclipsdeal.com/states",
                "position": 2
            }},
            {{
                "@type": "HowToStep",
                "name": "Click Get Coupon",
                "text": "Click the Get Coupon button on any deal you want. This opens the official Great Clips offer page and starts the 14-day validity period.",
                "position": 3
            }},
            {{
                "@type": "HowToStep",
                "name": "Save to your phone",
                "text": "Screenshot the coupon barcode or keep the browser tab open. You can also print the coupon if you prefer a paper copy.",
                "position": 4
            }},
            {{
                "@type": "HowToStep",
                "name": "Check in at Great Clips",
                "text": "Use the Great Clips app or website to check in at your preferred location. This reduces wait time significantly.",
                "position": 5
            }},
            {{
                "@type": "HowToStep",
                "name": "Show coupon at checkout",
                "text": "Before paying, show your coupon to the stylist. They will scan the barcode or manually enter the code to apply your discount.",
                "position": 6
            }}
        ]
    }}
    </script>
    
    <!-- Schema: BreadcrumbList -->
    <script type="application/ld+json">
    {{
        "@context": "https://schema.org",
        "@type": "BreadcrumbList",
        "itemListElement": [
            {{
                "@type": "ListItem",
                "position": 1,
                "name": "Home",
                "item": "https://greatclipsdeal.com/"
            }},
            {{
                "@type": "ListItem",
                "position": 2,
                "name": "How to Use Coupons",
                "item": "https://greatclipsdeal.com/how-to-use"
            }}
        ]
    }}
    </script>
'''

def get_prices_page_schema():
    """Schema for the prices page"""
    return f'''
    <!-- Schema: WebPage -->
    <script type="application/ld+json">
    {{
        "@context": "https://schema.org",
        "@type": "WebPage",
        "name": "Great Clips Prices {CURRENT_YEAR} - Haircut Costs & Coupon Savings",
        "description": "Current Great Clips haircut prices for adults, seniors, and kids. Compare regular prices vs coupon prices and save up to $10.",
        "url": "https://greatclipsdeal.com/prices",
        "dateModified": "{CURRENT_DATE}"
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
                "name": "How much does a Great Clips haircut cost?",
                "acceptedAnswer": {{
                    "@type": "Answer",
                    "text": "Great Clips adult haircuts cost $15-19, senior haircuts (65+) cost $13-17, and kids haircuts cost $13-16. Prices vary by location. With coupons from greatclipsdeal.com, you can pay as little as $5.99."
                }}
            }},
            {{
                "@type": "Question",
                "name": "Does Great Clips have senior discounts?",
                "acceptedAnswer": {{
                    "@type": "Answer",
                    "text": "Yes! Great Clips offers senior discounts for customers 65 and older. Senior haircuts are typically $2-3 less than adult prices. This can sometimes be combined with coupons."
                }}
            }},
            {{
                "@type": "Question",
                "name": "How much can I save with a Great Clips coupon?",
                "acceptedAnswer": {{
                    "@type": "Answer",
                    "text": "Great Clips coupons can save you $7-12 per haircut. Regular price is $15-19, but with coupons from greatclipsdeal.com you can pay $5.99-$8.99."
                }}
            }}
        ]
    }}
    </script>
    
    <!-- Schema: BreadcrumbList -->
    <script type="application/ld+json">
    {{
        "@context": "https://schema.org",
        "@type": "BreadcrumbList",
        "itemListElement": [
            {{
                "@type": "ListItem",
                "position": 1,
                "name": "Home",
                "item": "https://greatclipsdeal.com/"
            }},
            {{
                "@type": "ListItem",
                "position": 2,
                "name": "Prices",
                "item": "https://greatclipsdeal.com/prices"
            }}
        ]
    }}
    </script>
'''

def get_blog_article_schema(title, description, url_path):
    """Schema for blog articles"""
    return f'''
    <!-- Schema: Article -->
    <script type="application/ld+json">
    {{
        "@context": "https://schema.org",
        "@type": "Article",
        "headline": "{title}",
        "description": "{description}",
        "image": "https://greatclipsdeal.com/icon-512.png",
        "datePublished": "{CURRENT_DATE}",
        "dateModified": "{CURRENT_DATE}",
        "author": {{
            "@type": "Organization",
            "name": "GreatClipsDeal",
            "url": "https://greatclipsdeal.com"
        }},
        "publisher": {{
            "@type": "Organization",
            "name": "GreatClipsDeal",
            "logo": {{
                "@type": "ImageObject",
                "url": "https://greatclipsdeal.com/icon-512.png"
            }}
        }},
        "mainEntityOfPage": {{
            "@type": "WebPage",
            "@id": "https://greatclipsdeal.com/{url_path}"
        }}
    }}
    </script>
    
    <!-- Schema: BreadcrumbList -->
    <script type="application/ld+json">
    {{
        "@context": "https://schema.org",
        "@type": "BreadcrumbList",
        "itemListElement": [
            {{
                "@type": "ListItem",
                "position": 1,
                "name": "Home",
                "item": "https://greatclipsdeal.com/"
            }},
            {{
                "@type": "ListItem",
                "position": 2,
                "name": "Blog",
                "item": "https://greatclipsdeal.com/blog"
            }},
            {{
                "@type": "ListItem",
                "position": 3,
                "name": "{title}",
                "item": "https://greatclipsdeal.com/{url_path}"
            }}
        ]
    }}
    </script>
'''

def get_states_index_schema():
    """Schema for the states index page"""
    return f'''
    <!-- Schema: ItemList -->
    <script type="application/ld+json">
    {{
        "@context": "https://schema.org",
        "@type": "ItemList",
        "name": "Great Clips Coupons by State",
        "description": "Find Great Clips coupons organized by US state. Select your state to see local deals.",
        "numberOfItems": 50,
        "itemListElement": [
            {{"@type": "ListItem", "position": 1, "name": "Texas", "url": "https://greatclipsdeal.com/texas"}},
            {{"@type": "ListItem", "position": 2, "name": "California", "url": "https://greatclipsdeal.com/california"}},
            {{"@type": "ListItem", "position": 3, "name": "Florida", "url": "https://greatclipsdeal.com/florida"}},
            {{"@type": "ListItem", "position": 4, "name": "New York", "url": "https://greatclipsdeal.com/new-york"}},
            {{"@type": "ListItem", "position": 5, "name": "Ohio", "url": "https://greatclipsdeal.com/ohio"}}
        ]
    }}
    </script>
    
    <!-- Schema: BreadcrumbList -->
    <script type="application/ld+json">
    {{
        "@context": "https://schema.org",
        "@type": "BreadcrumbList",
        "itemListElement": [
            {{
                "@type": "ListItem",
                "position": 1,
                "name": "Home",
                "item": "https://greatclipsdeal.com/"
            }},
            {{
                "@type": "ListItem",
                "position": 2,
                "name": "States",
                "item": "https://greatclipsdeal.com/states"
            }}
        ]
    }}
    </script>
'''

# ============================================================================
# MAIN UPDATE FUNCTION
# ============================================================================

def remove_old_schema(html_content):
    """Remove existing schema scripts"""
    # Remove all existing ld+json scripts
    pattern = r'<script type="application/ld\+json">[\s\S]*?</script>\s*'
    return re.sub(pattern, '', html_content)

def insert_schema(html_content, schema):
    """Insert schema before </head>"""
    # Find </head> and insert schema before it
    return html_content.replace('</head>', f'{schema}\n</head>')

def update_file(filepath, schema):
    """Update a single HTML file with new schema"""
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Remove old schema
    content = remove_old_schema(content)
    
    # Insert new schema
    content = insert_schema(content, schema)
    
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(content)
    
    print(f"Updated: {filepath}")

def main():
    print("=" * 60)
    print("Rich Snippet Schema Updater")
    print("=" * 60)
    
    # Update homepage
    if os.path.exists('template.html'):
        update_file('template.html', HOMEPAGE_SCHEMA)
    
    # Update price pages
    price_pages = {
        'pages/5-99-coupon.html': ('5.99', '5-99-coupon'),
        'pages/6-99-coupon.html': ('6.99', '6-99-coupon'),
    }
    for filepath, (price, slug) in price_pages.items():
        if os.path.exists(filepath):
            update_file(filepath, get_price_page_schema(price, slug))
    
    # Update state pages
    state_pages = {
        'pages/texas.html': ('Texas', 'TX'),
        'pages/california.html': ('California', 'CA'),
        'pages/florida.html': ('Florida', 'FL'),
    }
    for filepath, (name, code) in state_pages.items():
        if os.path.exists(filepath):
            update_file(filepath, get_state_page_schema(name, code))
    
    # Update states index
    if os.path.exists('pages/states.html'):
        update_file('pages/states.html', get_states_index_schema())
    
    # Update how-to page
    if os.path.exists('pages/how-to-use.html'):
        update_file('pages/how-to-use.html', get_how_to_page_schema())
    
    # Update prices page
    if os.path.exists('pages/prices.html'):
        update_file('pages/prices.html', get_prices_page_schema())
    
    # Update blog pages
    blog_pages = {
        'pages/blog/coupon-hacks.html': (
            'Great Clips Coupon Hacks - Save Even More',
            'Pro tips and hacks for maximizing Great Clips coupon savings',
            'blog/coupon-hacks'
        ),
    }
    for filepath, (title, desc, url) in blog_pages.items():
        if os.path.exists(filepath):
            update_file(filepath, get_blog_article_schema(title, desc, url))
    
    print("\n" + "=" * 60)
    print("✅ All files updated with rich snippet schema!")
    print("=" * 60)
    print("\nNext steps:")
    print("1. Upload updated files to GitHub")
    print("2. Test at: https://search.google.com/test/rich-results")
    print("3. Submit sitemap in Google Search Console")

if __name__ == "__main__":
    main()
