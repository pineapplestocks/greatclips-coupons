#!/usr/bin/env python3
"""
Geographic market model for Great Clips coupons.

Great Clips issues coupons at three scopes:
  * national   - "Valid at participating US locations"
  * area       - "participating Chicagoland", "Greater Los Angeles", "Denver"
  * salon      - a single street address

The area scope is where the site was losing traffic: a Chicagoland coupon is
valid at ~90 suburbs, but nothing on the site said so, so Schaumburg and Cypress
never ranked. This module builds the missing link.

Two things live here:

1. build_metros() clusters the ~2,600 cities that have a salon into metro
   markets. Anchors are chosen greedily from the cities with the most salons;
   every other city joins the nearest anchor whose reach covers it. Anchor reach
   scales with salon count, so Houston pulls in Cypress/Katy/Conroe while
   Milwaukee stays independent of Chicago instead of chaining into one blob.

2. resolve_area() maps a coupon's market string onto those metros, using a
   nickname table ("Chicagoland" -> Chicago, "DFW" -> Dallas + Fort Worth) plus
   token matching against real city names, which handles the hyphenated market
   names Great Clips uses ("Leduc-Ft Sask-Sherwood Park-St Albert").
"""

from __future__ import annotations

import json
import math
import re
import unicodedata
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
SALONS_FILE = REPO_ROOT / "data" / "salons.json"
METROS_FILE = REPO_ROOT / "data" / "metros.json"

EARTH_RADIUS_MI = 3958.8

# Anchor reach in miles, keyed on how many salons sit within DENSITY_RADIUS_MI of
# the anchor - not on the anchor city's own count. Salons in a big metro are
# spread across dozens of suburbs, so no single municipality ever looks large;
# sizing by its own count fragmented Chicagoland into a dozen little markets.
DENSITY_RADIUS_MI = 30.0
REACH_TIERS = [
    (120, 55.0),  # dense metro -> Chicago, Houston, DFW, Phoenix
    (60, 45.0),   # large metro -> Nashville, Charlotte, Kansas City
    (25, 35.0),   # mid-size metro
    (8, 25.0),    # small metro
    (0, 18.0),    # isolated towns keep a tight footprint
]

# Principal cities in rough metro-prominence order, used only to NAME a market.
# The clustering anchor is a salon-density centroid, which in most metros lands in
# a suburb (Great Clips builds in strip malls, not downtown cores) - so density
# picked "Glen Ellyn" for Chicagoland and "Farmington" for Detroit. Naming from
# this list instead gives markets the names searchers and LLMs actually use.
PRINCIPAL_CITIES = [
    "New York, NY", "Los Angeles, CA", "Chicago, IL", "Houston, TX",
    "Phoenix, AZ", "Philadelphia, PA", "San Antonio, TX", "San Diego, CA",
    "Dallas, TX", "Austin, TX", "Jacksonville, FL", "Fort Worth, TX",
    "San Jose, CA", "Columbus, OH", "Charlotte, NC", "Indianapolis, IN",
    "San Francisco, CA", "Seattle, WA", "Denver, CO", "Washington, DC",
    "Boston, MA", "Nashville, TN", "Las Vegas, NV", "Portland, OR",
    "Detroit, MI", "Memphis, TN", "Louisville, KY", "Baltimore, MD",
    "Milwaukee, WI", "Albuquerque, NM", "Tucson, AZ", "Fresno, CA",
    "Sacramento, CA", "Kansas City, MO", "Mesa, AZ", "Atlanta, GA",
    "Omaha, NE", "Colorado Springs, CO", "Raleigh, NC", "Virginia Beach, VA",
    "Miami, FL", "Oakland, CA", "Minneapolis, MN", "Tulsa, OK",
    "Bakersfield, CA", "Wichita, KS", "Arlington, TX", "Aurora, CO",
    "Tampa, FL", "New Orleans, LA", "Cleveland, OH", "Anaheim, CA",
    "Honolulu, HI", "Riverside, CA", "Lexington, KY", "Stockton, CA",
    "Saint Paul, MN", "Cincinnati, OH", "Saint Louis, MO", "Pittsburgh, PA",
    "Greensboro, NC", "Anchorage, AK", "Plano, TX", "Orlando, FL",
    "Irvine, CA", "Newark, NJ", "Durham, NC", "Chula Vista, CA",
    "Toledo, OH", "Fort Wayne, IN", "Saint Petersburg, FL", "Laredo, TX",
    "Jersey City, NJ", "Chandler, AZ", "Madison, WI", "Lubbock, TX",
    "Scottsdale, AZ", "Reno, NV", "Buffalo, NY", "Gilbert, AZ",
    "Glendale, AZ", "North Las Vegas, NV", "Winston Salem, NC", "Chesapeake, VA",
    "Norfolk, VA", "Fremont, CA", "Garland, TX", "Irving, TX",
    "Hialeah, FL", "Richmond, VA", "Boise, ID", "Spokane, WA",
    "Baton Rouge, LA", "Tacoma, WA", "San Bernardino, CA", "Modesto, CA",
    "Fontana, CA", "Des Moines, IA", "Moreno Valley, CA", "Santa Clarita, CA",
    "Fayetteville, NC", "Birmingham, AL", "Oxnard, CA", "Rochester, NY",
    "Port Saint Lucie, FL", "Grand Rapids, MI", "Huntsville, AL", "Salt Lake City, UT",
    "Frisco, TX", "Yonkers, NY", "Amarillo, TX", "Glendale, CA",
    "Huntington Beach, CA", "McKinney, TX", "Montgomery, AL", "Augusta, GA",
    "Aurora, IL", "Akron, OH", "Little Rock, AR", "Tempe, AZ",
    "Columbus, GA", "Overland Park, KS", "Grand Prairie, TX", "Tallahassee, FL",
    "Cape Coral, FL", "Mobile, AL", "Knoxville, TN", "Shreveport, LA",
    "Worcester, MA", "Ontario, CA", "Vancouver, WA", "Sioux Falls, SD",
    "Chattanooga, TN", "Brownsville, TX", "Fort Lauderdale, FL", "Providence, RI",
    "Newport News, VA", "Rancho Cucamonga, CA", "Santa Rosa, CA", "Peoria, AZ",
    "Oceanside, CA", "Elk Grove, CA", "Salem, OR", "Pembroke Pines, FL",
    "Eugene, OR", "Garden Grove, CA", "Cary, NC", "Fort Collins, CO",
    "Corona, CA", "Springfield, MO", "Jackson, MS", "Alexandria, VA",
    "Hayward, CA", "Clarksville, TN", "Lakewood, CO", "Lancaster, CA",
    "Salinas, CA", "Palmdale, CA", "Hollywood, FL", "Springfield, MA",
    "Macon, GA", "Kansas City, KS", "Sunnyvale, CA", "Pomona, CA",
    "Killeen, TX", "Escondido, CA", "Pasadena, TX", "Naperville, IL",
    "Bellevue, WA", "Joliet, IL", "Murfreesboro, TN", "Rockford, IL",
    "Paterson, NJ", "Savannah, GA", "Bridgeport, CT", "Torrance, CA",
    "McAllen, TX", "Syracuse, NY", "Surprise, AZ", "Denton, TX",
    "Roseville, CA", "Thornton, CO", "Miramar, FL", "Pasadena, CA",
    "Mesquite, TX", "Olathe, KS", "Dayton, OH", "Carrollton, TX",
    "Waco, TX", "Orange, CA", "Fullerton, CA", "Charleston, SC",
    "West Valley City, UT", "Visalia, CA", "Hampton, VA", "Gainesville, FL",
    "Warren, MI", "Coral Springs, FL", "Cedar Rapids, IA", "Round Rock, TX",
    "Sterling Heights, MI", "Kent, WA", "Columbia, SC", "Santa Clara, CA",
    "New Haven, CT", "Stamford, CT", "Concord, CA", "Elizabeth, NJ",
    "Athens, GA", "Thousand Oaks, CA", "Lafayette, LA", "Simi Valley, CA",
    "Topeka, KS", "Norman, OK", "Fargo, ND", "Wilmington, NC",
    "Abilene, TX", "Odessa, TX", "Columbia, MO", "Pearland, TX",
    "Victorville, CA", "Hartford, CT", "Vallejo, CA", "Allentown, PA",
    "Berkeley, CA", "Richardson, TX", "Arvada, CO", "Ann Arbor, MI",
    "Rochester, MN", "Cambridge, MA", "Sugar Land, TX", "Lansing, MI",
    "Evansville, IN", "College Station, TX", "Fairfield, CA", "Clearwater, FL",
    "Beaumont, TX", "Independence, MO", "Provo, UT", "West Jordan, UT",
    "Murrieta, CA", "Palm Bay, FL", "El Monte, CA", "Carlsbad, CA",
    "North Charleston, SC", "Temecula, CA", "Clovis, CA", "Springfield, IL",
    "Meridian, ID", "Westminster, CO", "Costa Mesa, CA", "High Point, NC",
    "Manchester, NH", "Pueblo, CO", "Lakeland, FL", "Pompano Beach, FL",
    "West Palm Beach, FL", "Antioch, CA", "Everett, WA", "Downey, CA",
    "Lowell, MA", "Centennial, CO", "Elgin, IL", "Richmond, CA",
    "Peoria, IL", "Broken Arrow, OK", "Miami Gardens, FL", "Billings, MT",
    "Jurupa Valley, CA", "Sandy Springs, GA", "Gresham, OR", "Lewisville, TX",
    "Hillsboro, OR", "Ventura, CA", "Greeley, CO", "Inglewood, CA",
    "Waterbury, CT", "League City, TX", "Santa Maria, CA", "Tyler, TX",
    "Davie, FL", "Lakewood, NJ", "Daly City, CA", "Boulder, CO",
    "Allen, TX", "West Covina, CA", "Sparks, NV", "Wichita Falls, TX",
    "Green Bay, WI", "San Mateo, CA", "Norwalk, CA", "Rialto, CA",
    "Las Cruces, NM", "Chico, CA", "El Cajon, CA", "Burbank, CA",
    "South Bend, IN", "Renton, WA", "Vista, CA", "Davenport, IA",
    "Edinburg, TX", "Tuscaloosa, AL", "Carmel, IN", "Spokane Valley, WA",
    "San Angelo, TX", "Vacaville, CA", "Clinton, MI", "Bend, OR",
    "Woodbridge, NJ", "Palm Coast, FL", "Bellingham, WA", "Lees Summit, MO",
    "Sioux City, IA", "Greenville, SC", "Appleton, WI", "Duluth, MN",
    "Kalamazoo, MI", "Bloomington, IL", "Fort Smith, AR", "Yakima, WA",
    "Rock Hill, SC", "Kennewick, WA", "Flint, MI", "Muncie, IN",
    "Lynchburg, VA", "Asheville, NC", "Erie, PA", "Scranton, PA",
    "Harrisburg, PA", "York, PA", "Reading, PA", "Bethlehem, PA",
    "Fayetteville, AR", "Bentonville, AR", "Rogers, AR", "Springdale, AR",
    "Ogden, UT", "Orem, UT", "Sandy, UT", "Layton, UT",
    "Toms River, NJ", "Cherry Hill, NJ", "Edison, NJ", "New Brunswick, NJ",
    "Wilmington, DE", "Dover, DE", "Frederick, MD", "Rockville, MD",
    "Silver Spring, MD", "Annapolis, MD", "Arlington, VA", "Fairfax, VA",
    "Roanoke, VA", "Charlottesville, VA", "Fredericksburg, VA", "Harrisonburg, VA",
    "Bowling Green, KY", "Owensboro, KY", "Johnson City, TN", "Kingsport, TN",
    "Jackson, TN", "Florence, AL", "Dothan, AL", "Auburn, AL",
    "Biloxi, MS", "Hattiesburg, MS", "Gulfport, MS", "Metairie, LA",
    "Bossier City, LA", "Monroe, LA", "Alexandria, LA", "Lake Charles, LA",
    "Texarkana, TX", "Longview, TX", "Temple, TX", "New Braunfels, TX",
    "Corpus Christi, TX", "Harlingen, TX", "Midland, TX", "Bryan, TX",
    "Conway, AR", "Jonesboro, AR", "Hot Springs, AR", "Joplin, MO",
    "Saint Joseph, MO", "Jefferson City, MO", "Cape Girardeau, MO", "Bloomington, IN",
    "Lafayette, IN", "Terre Haute, IN", "Elkhart, IN", "Mishawaka, IN",
    "Merrillville, IN", "Valparaiso, IN", "Champaign, IL", "Decatur, IL",
    "Moline, IL", "Bettendorf, IA", "Iowa City, IA", "Ames, IA",
    "Waterloo, IA", "Dubuque, IA", "Council Bluffs, IA", "Lincoln, NE",
    "Grand Island, NE", "Bellevue, NE", "Rapid City, SD", "Bismarck, ND",
    "Grand Forks, ND", "Minot, ND", "Saint Cloud, MN", "Mankato, MN",
    "Eau Claire, WI", "La Crosse, WI", "Oshkosh, WI", "Sheboygan, WI",
    "Janesville, WI", "Wausau, WI", "Traverse City, MI", "Saginaw, MI",
    "Muskegon, MI", "Battle Creek, MI", "Jackson, MI", "Holland, MI",
    "Canton, OH", "Youngstown, OH", "Springfield, OH", "Lima, OH",
    "Mansfield, OH", "Findlay, OH", "Newark, OH", "Zanesville, OH",
    "Huntington, WV", "Charleston, WV", "Morgantown, WV", "Parkersburg, WV",
    "Altoona, PA", "State College, PA", "Williamsport, PA", "Lancaster, PA",
    "Albany, NY", "Schenectady, NY", "Utica, NY", "Binghamton, NY",
    "Poughkeepsie, NY", "Newburgh, NY", "Ithaca, NY", "Watertown, NY",
    "Portland, ME", "Bangor, ME", "Nashua, NH", "Concord, NH",
    "Burlington, VT", "Warwick, RI", "Danbury, CT", "Norwich, CT",
    "Greenville, NC", "Jacksonville, NC", "Concord, NC", "Gastonia, NC",
    "Hickory, NC", "Burlington, NC", "Spartanburg, SC", "Florence, SC",
    "Myrtle Beach, SC", "Summerville, SC", "Albany, GA", "Valdosta, GA",
    "Warner Robins, GA", "Marietta, GA", "Alpharetta, GA", "Roswell, GA",
    "Gainesville, GA", "Ocala, FL", "Daytona Beach, FL", "Melbourne, FL",
    "Sarasota, FL", "Bradenton, FL", "Fort Myers, FL", "Naples, FL",
    "Kissimmee, FL", "Sanford, FL", "Panama City, FL", "Pensacola, FL",
    "Boca Raton, FL", "Boynton Beach, FL", "Delray Beach, FL", "Jupiter, FL",
    "Stuart, FL", "Vero Beach, FL", "Titusville, FL", "Leesburg, FL",
    "Flagstaff, AZ", "Yuma, AZ", "Prescott, AZ", "Casa Grande, AZ",
    "Santa Fe, NM", "Rio Rancho, NM", "Farmington, NM", "Roswell, NM",
    "Grand Junction, CO", "Loveland, CO", "Longmont, CO", "Castle Rock, CO",
    "Cheyenne, WY", "Casper, WY", "Missoula, MT", "Bozeman, MT",
    "Great Falls, MT", "Idaho Falls, ID", "Pocatello, ID", "Coeur Dalene, ID",
    "Nampa, ID", "Twin Falls, ID", "Saint George, UT", "Logan, UT",
    "Carson City, NV", "Medford, OR", "Corvallis, OR", "Albany, OR",
    "Olympia, WA", "Bremerton, WA", "Wenatchee, WA", "Mount Vernon, WA",
    "Redding, CA", "Merced, CA", "Turlock, CA", "Napa, CA",
    "Santa Cruz, CA", "San Luis Obispo, CA", "Santa Barbara, CA", "Hanford, CA",
    "Lompoc, CA", "Yuba City, CA", "Tracy, CA", "Manteca, CA",
]

_PRINCIPAL_RANK: dict[str, int] = {}


def _principal_rank_table() -> dict[str, int]:
    """Built on first use, since it needs normalize_city() defined below."""
    if not _PRINCIPAL_RANK:
        for i, spec in enumerate(PRINCIPAL_CITIES):
            name, _, state = spec.rpartition(",")
            _PRINCIPAL_RANK[f"{normalize_city(name)}|{state.strip()}"] = i
    return _PRINCIPAL_RANK

# Markets that are genuinely known by a twin name. Only these produce a
# hyphenated market name; everything else takes a single city name.
TWIN_MARKETS = [
    ("Dallas, TX", "Fort Worth, TX"),
    ("Minneapolis, MN", "Saint Paul, MN"),
    ("Tampa, FL", "Saint Petersburg, FL"),
    ("Raleigh, NC", "Durham, NC"),
    ("Greensboro, NC", "Winston Salem, NC"),
    ("San Francisco, CA", "Oakland, CA"),
    ("Norfolk, VA", "Virginia Beach, VA"),
    ("Allentown, PA", "Bethlehem, PA"),
    ("Davenport, IA", "Moline, IL"),
    ("Kennewick, WA", "Richland, WA"),
    ("Bryan, TX", "College Station, TX"),
    ("Midland, TX", "Odessa, TX"),
    ("Champaign, IL", "Urbana, IL"),
    ("Fayetteville, AR", "Springdale, AR"),
    ("Scranton, PA", "Wilkes Barre, PA"),
    ("Melbourne, FL", "Palm Bay, FL"),
    ("Sarasota, FL", "Bradenton, FL"),
    ("South Bend, IN", "Mishawaka, IN"),
    ("Johnson City, TN", "Kingsport, TN"),
    ("Kansas City, MO", "Overland Park, KS"),
]


# Coordinates for principal cities that have NO Great Clips salon of their own.
# Great Clips is a strip-mall brand, so it skips dense urban cores entirely -
# there is not one salon in New York City, Philadelphia, Boston, Detroit or Miami,
# yet each anchors a large suburban market. Without these coordinates a market
# ends up labelled "Warren, MI" instead of "Detroit", and a coupon issued for the
# "Detroit" area matches nothing at all.
METRO_CENTERS: dict[str, tuple[float, float]] = {
    "New York, NY": (40.7128, -74.0060),
    "Philadelphia, PA": (39.9526, -75.1652),
    "Boston, MA": (42.3601, -71.0589),
    "Detroit, MI": (42.3314, -83.0458),
    "Miami, FL": (25.7617, -80.1918),
    "Fort Lauderdale, FL": (26.1224, -80.1373),
    "West Palm Beach, FL": (26.7153, -80.0534),
    "Miami Gardens, FL": (25.9420, -80.2456),
    "Davie, FL": (26.0765, -80.2521),
    "Sanford, FL": (28.8029, -81.2695),
    "Jupiter, FL": (26.9342, -80.0942),
    "Leesburg, FL": (28.8108, -81.8779),
    "Newark, NJ": (40.7357, -74.1724),
    "Paterson, NJ": (40.9168, -74.1718),
    "Elizabeth, NJ": (40.6639, -74.2107),
    "Woodbridge, NJ": (40.5576, -74.2846),
    "Edison, NJ": (40.5187, -74.4121),
    "New Brunswick, NJ": (40.4862, -74.4518),
    "Lakewood, NJ": (40.0979, -74.2179),
    "Yonkers, NY": (40.9312, -73.8988),
    "Buffalo, NY": (42.8864, -78.8784),
    "Syracuse, NY": (43.0481, -76.1474),
    "Albany, NY": (42.6526, -73.7562),
    "Utica, NY": (43.1009, -75.2327),
    "Binghamton, NY": (42.0987, -75.9180),
    "Poughkeepsie, NY": (41.7004, -73.9210),
    "Newburgh, NY": (41.5034, -74.0104),
    "Ithaca, NY": (42.4440, -76.5019),
    "Watertown, NY": (43.9748, -75.9108),
    "Worcester, MA": (42.2626, -71.8023),
    "Springfield, MA": (42.1015, -72.5898),
    "Cambridge, MA": (42.3736, -71.1097),
    "Lowell, MA": (42.6334, -71.3162),
    "Providence, RI": (41.8240, -71.4128),
    "Hartford, CT": (41.7658, -72.6734),
    "New Haven, CT": (41.3083, -72.9279),
    "Bridgeport, CT": (41.1865, -73.1952),
    "Stamford, CT": (41.0534, -73.5387),
    "Waterbury, CT": (41.5582, -73.0515),
    "Danbury, CT": (41.3948, -73.4540),
    "Portland, ME": (43.6591, -70.2568),
    "Bangor, ME": (44.8016, -68.7712),
    "Burlington, VT": (44.4759, -73.2121),
    "Scranton, PA": (41.4090, -75.6624),
    "Bethlehem, PA": (40.6259, -75.3705),
    "Silver Spring, MD": (38.9907, -77.0261),
    "Rockville, MD": (39.0840, -77.1528),
    "Frederick, MD": (39.4143, -77.4105),
    "Annapolis, MD": (38.9784, -76.4922),
    "Harrisonburg, VA": (38.4496, -78.8689),
    "Huntington, WV": (38.4192, -82.4452),
    "New Orleans, LA": (29.9511, -90.0715),
    "Metairie, LA": (29.9841, -90.1529),
    "Baton Rouge, LA": (30.4515, -91.1871),
    "Lafayette, LA": (30.2241, -92.0198),
    "Bossier City, LA": (32.5160, -93.7321),
    "Monroe, LA": (32.5093, -92.1193),
    "Alexandria, LA": (31.3113, -92.4451),
    "Lake Charles, LA": (30.2266, -93.2174),
    "Jackson, MS": (32.2988, -90.1848),
    "Gulfport, MS": (30.3674, -89.0928),
    "Beaumont, TX": (30.0802, -94.1266),
    "Pasadena, TX": (29.6911, -95.2091),
    "Brownsville, TX": (25.9017, -97.4975),
    "Harlingen, TX": (26.1906, -97.6961),
    "Edinburg, TX": (26.3017, -98.1633),
    "Anaheim, CA": (33.8366, -117.9143),
    "Garden Grove, CA": (33.7743, -117.9380),
    "Orange, CA": (33.7879, -117.8531),
    "Costa Mesa, CA": (33.6411, -117.9187),
    "Glendale, CA": (34.1425, -118.2551),
    "Pasadena, CA": (34.1478, -118.1445),
    "El Monte, CA": (34.0686, -118.0276),
    "West Covina, CA": (34.0686, -117.9390),
    "Norwalk, CA": (33.9022, -118.0817),
    "Inglewood, CA": (33.9617, -118.3531),
    "Lancaster, CA": (34.6868, -118.1542),
    "Palmdale, CA": (34.5794, -118.1165),
    "Santa Clarita, CA": (34.3917, -118.5426),
    "Moreno Valley, CA": (33.9425, -117.2297),
    "Hayward, CA": (37.6688, -122.0808),
    "Berkeley, CA": (37.8715, -122.2730),
    "Richmond, CA": (37.9358, -122.3477),
    "Concord, CA": (37.9780, -122.0311),
    "Vallejo, CA": (38.1041, -122.2566),
    "Daly City, CA": (37.6879, -122.4702),
    "San Mateo, CA": (37.5630, -122.3255),
    "Carlsbad, CA": (33.1581, -117.3506),
    "Santa Barbara, CA": (34.4208, -119.6982),
    "San Luis Obispo, CA": (35.2828, -120.6596),
    "Lompoc, CA": (34.6391, -120.4579),
    "Winston Salem, NC": (36.0999, -80.2442),
    "North Charleston, SC": (32.8546, -79.9748),
    "Albany, GA": (31.5785, -84.1557),
    "Hialeah, FL": (25.8576, -80.2781),
    "Olympia, WA": (47.0379, -122.9007),
    "Coeur Dalene, ID": (47.6777, -116.7805),
    "Logan, UT": (41.7355, -111.8344),
    "Roswell, NM": (33.3943, -104.5230),
    "Sheboygan, WI": (43.7508, -87.7145),
    "Clinton, MI": (42.5872, -82.9200),
}


def principal_rank(city: dict) -> int | None:
    """Prominence rank of a city, or None if it is not a principal city."""
    return _principal_rank_table().get(
        f"{normalize_city(city['city'])}|{city['state']}"
    )

STATE_NAMES = {
    "AL": "Alabama", "AK": "Alaska", "AZ": "Arizona", "AR": "Arkansas",
    "CA": "California", "CO": "Colorado", "CT": "Connecticut", "DC": "District of Columbia",
    "DE": "Delaware", "FL": "Florida", "GA": "Georgia", "HI": "Hawaii",
    "ID": "Idaho", "IL": "Illinois", "IN": "Indiana", "IA": "Iowa",
    "KS": "Kansas", "KY": "Kentucky", "LA": "Louisiana", "ME": "Maine",
    "MD": "Maryland", "MA": "Massachusetts", "MI": "Michigan", "MN": "Minnesota",
    "MS": "Mississippi", "MO": "Missouri", "MT": "Montana", "NE": "Nebraska",
    "NV": "Nevada", "NH": "New Hampshire", "NJ": "New Jersey", "NM": "New Mexico",
    "NY": "New York", "NC": "North Carolina", "ND": "North Dakota", "OH": "Ohio",
    "OK": "Oklahoma", "OR": "Oregon", "PA": "Pennsylvania", "RI": "Rhode Island",
    "SC": "South Carolina", "SD": "South Dakota", "TN": "Tennessee", "TX": "Texas",
    "UT": "Utah", "VT": "Vermont", "VA": "Virginia", "WA": "Washington",
    "WV": "West Virginia", "WI": "Wisconsin", "WY": "Wyoming",
}

# Regional nicknames and marketing-co-op names that are not city names. Each maps
# to the real anchor cities the promotion covers, as "City, ST".
AREA_ALIASES: dict[str, list[str]] = {
    "chicagoland": ["Chicago, IL"],
    "chicago suburbs": ["Chicago, IL"],
    "chicago metro": ["Chicago, IL"],
    "northwest indiana": ["Merrillville, IN", "Chicago, IL"],
    "dfw": ["Dallas, TX", "Fort Worth, TX"],
    "dallas fort worth": ["Dallas, TX", "Fort Worth, TX"],
    "dallas ft worth": ["Dallas, TX", "Fort Worth, TX"],
    "metroplex": ["Dallas, TX", "Fort Worth, TX"],
    "north texas": ["Dallas, TX", "Fort Worth, TX"],
    "twin cities": ["Minneapolis, MN", "Saint Paul, MN"],
    "bay area": ["San Francisco, CA", "San Jose, CA", "Oakland, CA"],
    "san francisco bay area": ["San Francisco, CA", "San Jose, CA", "Oakland, CA"],
    "east bay": ["Oakland, CA", "Concord, CA"],
    "south bay": ["San Jose, CA"],
    "greater los angeles": ["Los Angeles, CA", "Long Beach, CA"],
    "los angeles metro": ["Los Angeles, CA", "Long Beach, CA"],
    "inland empire": ["Riverside, CA", "San Bernardino, CA"],
    "orange county": ["Anaheim, CA", "Irvine, CA", "Santa Ana, CA"],
    "central valley": ["Fresno, CA", "Modesto, CA", "Bakersfield, CA"],
    "sacramento valley": ["Sacramento, CA"],
    "puget sound": ["Seattle, WA", "Tacoma, WA"],
    "greater seattle": ["Seattle, WA", "Tacoma, WA"],
    "western washington": ["Seattle, WA", "Tacoma, WA", "Olympia, WA"],
    "eastern washington": ["Spokane, WA", "Kennewick, WA"],
    "tri cities": ["Kennewick, WA", "Richland, WA", "Pasco, WA"],
    "portland metro": ["Portland, OR"],
    "willamette valley": ["Portland, OR", "Salem, OR", "Eugene, OR"],
    "treasure valley": ["Boise, ID", "Nampa, ID"],
    "magic valley": ["Twin Falls, ID"],
    "wasatch front": ["Salt Lake City, UT", "Provo, UT", "Ogden, UT"],
    "front range": ["Denver, CO", "Colorado Springs, CO", "Fort Collins, CO"],
    "denver metro": ["Denver, CO"],
    "upper rio grande valley": ["El Paso, TX", "Las Cruces, NM"],
    "rio grande valley": ["McAllen, TX", "Brownsville, TX", "Harlingen, TX"],
    "permian basin": ["Midland, TX", "Odessa, TX"],
    "golden triangle": ["Beaumont, TX", "Port Arthur, TX"],
    "brazos valley": ["College Station, TX", "Bryan, TX"],
    "coastal bend": ["Corpus Christi, TX"],
    "hill country": ["San Antonio, TX", "New Braunfels, TX"],
    "greater houston": ["Houston, TX"],
    "houston metro": ["Houston, TX"],
    "central texas": ["Austin, TX", "Waco, TX"],
    "south florida": ["Miami, FL", "Fort Lauderdale, FL", "West Palm Beach, FL"],
    "tampa bay": ["Tampa, FL", "Saint Petersburg, FL", "Clearwater, FL"],
    "central florida": ["Orlando, FL"],
    "first coast": ["Jacksonville, FL"],
    "space coast": ["Melbourne, FL", "Palm Bay, FL"],
    "emerald coast": ["Pensacola, FL", "Fort Walton Beach, FL"],
    "southwest florida": ["Fort Myers, FL", "Naples, FL", "Cape Coral, FL"],
    "research triangle": ["Raleigh, NC", "Durham, NC", "Chapel Hill, NC"],
    "triangle": ["Raleigh, NC", "Durham, NC", "Chapel Hill, NC"],
    "piedmont triad": ["Greensboro, NC", "Winston Salem, NC", "High Point, NC"],
    "triad": ["Greensboro, NC", "Winston Salem, NC", "High Point, NC"],
    "charlotte metro": ["Charlotte, NC"],
    "upstate": ["Greenville, SC", "Spartanburg, SC"],
    "lowcountry": ["Charleston, SC", "Summerville, SC"],
    "grand strand": ["Myrtle Beach, SC"],
    "hampton roads": ["Virginia Beach, VA", "Norfolk, VA", "Chesapeake, VA"],
    "tidewater": ["Virginia Beach, VA", "Norfolk, VA"],
    "northern virginia": ["Arlington, VA", "Alexandria, VA", "Fairfax, VA"],
    "nova": ["Arlington, VA", "Alexandria, VA", "Fairfax, VA"],
    "dmv": ["Washington, DC", "Arlington, VA", "Silver Spring, MD"],
    "dc metro": ["Washington, DC", "Arlington, VA", "Silver Spring, MD"],
    "delaware valley": ["Philadelphia, PA"],
    "lehigh valley": ["Allentown, PA", "Bethlehem, PA", "Easton, PA"],
    "greater philadelphia": ["Philadelphia, PA"],
    "greater boston": ["Boston, MA"],
    "greater cincinnati": ["Cincinnati, OH"],
    "greater cleveland": ["Cleveland, OH"],
    "greater columbus": ["Columbus, OH"],
    "northeast ohio": ["Cleveland, OH", "Akron, OH", "Canton, OH"],
    "miami valley": ["Dayton, OH"],
    "michiana": ["South Bend, IN", "Mishawaka, IN"],
    "quad cities": ["Davenport, IA", "Bettendorf, IA", "Moline, IL"],
    "kansas city metro": ["Kansas City, MO", "Overland Park, KS"],
    "greater st louis": ["Saint Louis, MO"],
    "st louis metro": ["Saint Louis, MO"],
    "metro detroit": ["Detroit, MI", "Warren, MI", "Troy, MI"],
    "west michigan": ["Grand Rapids, MI"],
    "greater phoenix": ["Phoenix, AZ", "Mesa, AZ", "Scottsdale, AZ"],
    "valley of the sun": ["Phoenix, AZ", "Mesa, AZ", "Scottsdale, AZ"],
    "east valley": ["Mesa, AZ", "Chandler, AZ", "Gilbert, AZ"],
    "west valley": ["Glendale, AZ", "Peoria, AZ", "Surprise, AZ"],
    "northern nevada": ["Reno, NV", "Carson City, NV"],
    "west nv": ["Reno, NV", "Carson City, NV"],
    "southern nevada": ["Las Vegas, NV", "Henderson, NV"],
    "las vegas valley": ["Las Vegas, NV", "Henderson, NV"],
    "greater nashville": ["Nashville, TN"],
    "middle tennessee": ["Nashville, TN", "Murfreesboro, TN"],
    "east tennessee": ["Knoxville, TN", "Chattanooga, TN"],
    "greater memphis": ["Memphis, TN"],
    "greater atlanta": ["Atlanta, GA"],
    "metro atlanta": ["Atlanta, GA"],
    "greater milwaukee": ["Milwaukee, WI"],
    "fox valley": ["Appleton, WI", "Oshkosh, WI", "Green Bay, WI"],
    "madison metro": ["Madison, WI"],
    "greater indianapolis": ["Indianapolis, IN"],
    "greater omaha": ["Omaha, NE"],
    "greater des moines": ["Des Moines, IA"],
    "greater oklahoma city": ["Oklahoma City, OK"],
    # Initialisms Great Clips uses in its own market names.
    "okc": ["Oklahoma City, OK"],
    "slc": ["Salt Lake City, UT"],
    "atx": ["Austin, TX"],
    "sa": ["San Antonio, TX"],
    "kc": ["Kansas City, MO", "Overland Park, KS"],
    "philly": ["Philadelphia, PA"],
    "pdx": ["Portland, OR"],
    "sd": ["San Diego, CA"],
    "sf": ["San Francisco, CA"],
    "abq": ["Albuquerque, NM"],
    "greater tulsa": ["Tulsa, OK"],
    "greater louisville": ["Louisville, KY"],
    "bluegrass": ["Lexington, KY"],
    "greater richmond": ["Richmond, VA"],
    "greater baltimore": ["Baltimore, MD"],
    "greater new york": ["New York, NY"],
    "new york metro": ["New York, NY"],
    "new york city": ["New York, NY"],
    "nyc": ["New York, NY"],
    "manhattan": ["New York, NY"],
    "brooklyn": ["New York, NY"],
    "queens": ["New York, NY"],
    "the bronx": ["New York, NY"],
    "staten island": ["New York, NY"],
    "long island": ["Hicksville, NY", "Huntington, NY"],
    "hudson valley": ["Poughkeepsie, NY", "Newburgh, NY"],
    "capital region": ["Albany, NY", "Schenectady, NY"],
    "central new york": ["Syracuse, NY", "Utica, NY"],
    "western new york": ["Buffalo, NY", "Rochester, NY"],
    "north jersey": ["Newark, NJ", "Paterson, NJ"],
    "central jersey": ["Edison, NJ", "New Brunswick, NJ"],
    "south jersey": ["Cherry Hill, NJ", "Vineland, NJ"],
    "jersey shore": ["Toms River, NJ", "Brick, NJ"],
    "greater birmingham": ["Birmingham, AL"],
    "gulf coast": ["Mobile, AL", "Pensacola, FL", "Biloxi, MS"],
    "greater new orleans": ["New Orleans, LA", "Metairie, LA"],
    "acadiana": ["Lafayette, LA"],
    "northwest arkansas": ["Fayetteville, AR", "Bentonville, AR", "Rogers, AR"],
    "central arkansas": ["Little Rock, AR", "North Little Rock, AR"],
    "greater kansas": ["Wichita, KS"],
    "greater albuquerque": ["Albuquerque, NM"],
    "northern colorado": ["Fort Collins, CO", "Greeley, CO"],
    "southern colorado": ["Colorado Springs, CO", "Pueblo, CO"],
    "greater salt lake": ["Salt Lake City, UT"],
    "utah valley": ["Provo, UT", "Orem, UT"],
    "greater grand rapids": ["Grand Rapids, MI"],
    "greater charleston": ["Charleston, SC"],
    "greater greenville": ["Greenville, SC"],
    "greater pittsburgh": ["Pittsburgh, PA"],
    "central pennsylvania": ["Harrisburg, PA", "Lancaster, PA", "York, PA"],
    "greater hartford": ["Hartford, CT"],
    "greater providence": ["Providence, RI"],
    "greater portland": ["Portland, OR"],
    "greater spokane": ["Spokane, WA"],
    "greater boise": ["Boise, ID"],
    "greater fargo": ["Fargo, ND", "West Fargo, ND", "Moorhead, MN"],
    "red river valley": ["Fargo, ND", "Grand Forks, ND"],
    "siouxland": ["Sioux City, IA", "Sioux Falls, SD"],
    "greater sioux falls": ["Sioux Falls, SD"],
    "greater billings": ["Billings, MT"],
    "greater anchorage": ["Anchorage, AK"],
    "greater honolulu": ["Honolulu, HI"],
}

# Great Clips runs Canadian salons too, and their market names collide with US
# city names - the Edmonton-area market "Leduc-Ft Sask-Sherwood Park-St Albert-
# Beaumont-Spruce Grove" matched Beaumont, Texas and leaked an Alberta coupon onto
# Texas pages. These markers plus the coherence check in resolve_area keep foreign
# markets out.
FOREIGN_MARKERS = re.compile(
    r"\b(?:calgary|edmonton|lethbridge|airdrie|okotoks|cochrane|leduc|sask|"
    r"saskatoon|saskatchewan|regina|sherwood park|st albert|spruce grove|"
    r"winnipeg|manitoba|toronto|ottawa|mississauga|brampton|hamilton on|"
    r"niagara falls|kitchener|waterloo on|london on|windsor on|barrie|oshawa|"
    r"vancouver bc|victoria bc|burnaby|surrey bc|richmond bc|kelowna|abbotsford|"
    r"halifax|moncton|fredericton|quebec|montreal|alberta|ontario ca|"
    r"british columbia|nova scotia|new brunswick ca|newfoundland)\b",
    re.I,
)

# A market string whose tokens mostly fail to match is more likely foreign or
# malformed than a real US market, so require this much agreement.
MIN_MATCH_RATIO = 0.34

# Noise words stripped from a coupon's market string before matching.
AREA_NOISE = re.compile(
    r"^(?:only\s+)?(?:valid\s+)?(?:at\s+)?(?:participating\s+)+|"
    r"\b(?:locations?|salons?|area|areas|metro|metropolitan|region|market|"
    r"and\s+surrounding|surrounding|greater)\b",
    re.I,
)


# ------------------------------------------------------------------- geo -----

def haversine_mi(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    """Great-circle distance in miles."""
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp = p2 - p1
    dl = math.radians(lng2 - lng1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * EARTH_RADIUS_MI * math.asin(math.sqrt(a))


def reach_for(density: int) -> float:
    """Anchor reach in miles for a given surrounding-salon density."""
    for threshold, miles in REACH_TIERS:
        if density >= threshold:
            return miles
    return REACH_TIERS[-1][1]


def slugify(text: str) -> str:
    text = unicodedata.normalize("NFKD", str(text))
    text = text.encode("ascii", "ignore").decode("ascii")
    text = re.sub(r"[^a-zA-Z0-9]+", "-", text).strip("-").lower()
    return re.sub(r"-{2,}", "-", text)


def normalize_city(name: str) -> str:
    """Fold city-name spelling variants so 'St. Louis' == 'Saint Louis'."""
    n = unicodedata.normalize("NFKD", str(name)).encode("ascii", "ignore").decode()
    n = n.lower().replace(".", " ").replace("'", "")
    n = re.sub(r"\s+", " ", n).strip()
    n = re.sub(r"^st\b", "saint", n)
    n = re.sub(r"^ft\b", "fort", n)
    n = re.sub(r"^mt\b", "mount", n)
    n = re.sub(r"^n\b", "north", n)
    n = re.sub(r"^s\b", "south", n)
    n = re.sub(r"^e\b", "east", n)
    n = re.sub(r"^w\b", "west", n)
    return n


# ---------------------------------------------------------------- cities -----

def load_salons(path: Path = SALONS_FILE) -> list[dict]:
    if not path.exists():
        raise SystemExit(
            f"{path} not found - run scripts/fetch_salons.py first."
        )
    with path.open(encoding="utf-8") as fh:
        return json.load(fh)["salons"]


def build_cities(salons: list[dict]) -> dict[str, dict]:
    """Group salons into cities keyed 'ST/normalized-slug'.

    Grouping runs on the normalized name because the locator spells the same city
    several ways - "Saint Louis", "St Louis" and "St. Louis" all appear in the
    feed. Keying on the raw name would split one city across three pages, each
    with a partial salon list. The display name (and therefore the URL slug) is
    then the spelling the feed uses most often, so St. Louis keeps the /st-louis
    slug people actually search for.
    """
    groups: dict[str, dict] = {}

    for salon in salons:
        if salon.get("country", "US") != "US":
            continue
        state, city = salon["state"], salon["city"]
        key = f"{state}/{slugify(normalize_city(city))}"
        entry = groups.setdefault(
            key, {"key": key, "state": state, "spellings": {}, "salons": []}
        )
        entry["spellings"][city] = entry["spellings"].get(city, 0) + 1
        entry["salons"].append(salon)

    cities: dict[str, dict] = {}
    used_slugs: set[str] = set()

    for key, entry in groups.items():
        # Most common spelling wins; longest breaks ties ("Saint" over "St").
        display = max(entry["spellings"].items(), key=lambda kv: (kv[1], len(kv[0])))[0]
        slug = slugify(display)
        if f"{entry['state']}/{slug}" in used_slugs:
            slug = slugify(normalize_city(display))
        used_slugs.add(f"{entry['state']}/{slug}")

        pts = [(s["lat"], s["lng"]) for s in entry["salons"] if s.get("lat") is not None]
        cities[key] = {
            "key": key,
            "city": display,
            "state": entry["state"],
            "state_name": STATE_NAMES.get(entry["state"], entry["state"]),
            "slug": slug,
            "salons": sorted(entry["salons"], key=lambda s: s["street"]),
            "salon_count": len(entry["salons"]),
            "lat": round(sum(p[0] for p in pts) / len(pts), 6) if pts else None,
            "lng": round(sum(p[1] for p in pts) / len(pts), 6) if pts else None,
            "aliases": sorted(n for n in entry["spellings"] if n != display),
        }

    return cities


# ---------------------------------------------------------------- metros -----

def _spatial_index(cities: list[dict], cell_deg: float = 0.75) -> dict:
    """Bucket cities into a coarse lat/lng grid so neighbour lookups stay cheap."""
    grid: dict[tuple[int, int], list[dict]] = {}
    for city in cities:
        cell = (int(city["lat"] // cell_deg), int(city["lng"] // cell_deg))
        grid.setdefault(cell, []).append(city)
    return {"grid": grid, "cell_deg": cell_deg}


def _neighbours(index: dict, city: dict, radius_mi: float) -> list[dict]:
    """Cities in the grid cells that could hold anything within radius_mi."""
    cell_deg = index["cell_deg"]
    span = int(radius_mi / (69.0 * cell_deg)) + 1
    base = (int(city["lat"] // cell_deg), int(city["lng"] // cell_deg))
    out: list[dict] = []
    for dy in range(-span, span + 1):
        for dx in range(-span, span + 1):
            out.extend(index["grid"].get((base[0] + dy, base[1] + dx), ()))
    return out


def compute_density(cities: dict[str, dict]) -> None:
    """Set city['density'] = salons within DENSITY_RADIUS_MI, including its own.

    This is the metro-size signal. Downtown Chicago has ~20 salons of its own but
    ~150 within 30 miles, which is what makes it outrank Schaumburg for anchor
    selection and earns it the widest reach tier.
    """
    geo = [c for c in cities.values() if c["lat"] is not None]
    index = _spatial_index(geo)

    for city in geo:
        total = 0
        for other in _neighbours(index, city, DENSITY_RADIUS_MI):
            if (
                haversine_mi(city["lat"], city["lng"], other["lat"], other["lng"])
                <= DENSITY_RADIUS_MI
            ):
                total += other["salon_count"]
        city["density"] = total

    for city in cities.values():
        city.setdefault("density", city["salon_count"])


def build_metros(cities: dict[str, dict]) -> dict[str, dict]:
    """Cluster cities into metro markets around greedily chosen anchors.

    Anchors are taken in descending density order, so the centre of each metro
    wins before its suburbs do. A city becomes a new anchor only when no existing
    anchor's reach already covers it, and every city then joins the nearest
    anchor that reaches it. Testing against an anchor's reach - rather than
    linking neighbour to neighbour - is what keeps the continuous suburb chain up
    I-94 from welding Chicago to Milwaukee into one market.
    """
    compute_density(cities)

    geo = [c for c in cities.values() if c["lat"] is not None]
    ordered = sorted(
        geo, key=lambda c: (-c["density"], -c["salon_count"], c["state"], c["city"])
    )
    index = _spatial_index(geo)

    anchors: list[dict] = []
    for city in ordered:
        covered = any(
            haversine_mi(city["lat"], city["lng"], a["lat"], a["lng"])
            <= reach_for(a["density"])
            for a in anchors
        )
        if not covered:
            anchors.append(city)

    metros: dict[str, dict] = {}
    for anchor in anchors:
        key = f"{anchor['state']}/{anchor['slug']}"
        metros[key] = {
            "key": key,
            "anchor_city": anchor["city"],
            "anchor_state": anchor["state"],
            "lat": anchor["lat"],
            "lng": anchor["lng"],
            "reach_mi": reach_for(anchor["density"]),
            "density": anchor["density"],
            "city_keys": [],
        }

    anchor_index = _spatial_index(anchors)
    max_reach = max(REACH_TIERS, key=lambda t: t[1])[1]

    for city in ordered:
        best_key, best_dist = None, None
        for anchor in _neighbours(anchor_index, city, max_reach):
            d = haversine_mi(city["lat"], city["lng"], anchor["lat"], anchor["lng"])
            if d <= reach_for(anchor["density"]) and (
                best_dist is None or d < best_dist
            ):
                best_key = f"{anchor['state']}/{anchor['slug']}"
                best_dist = d
        if best_key is None:  # should not happen; anchors cover every city
            best_key = f"{city['state']}/{city['slug']}"
            metros.setdefault(
                best_key,
                {
                    "key": best_key,
                    "anchor_city": city["city"],
                    "anchor_state": city["state"],
                    "lat": city["lat"],
                    "lng": city["lng"],
                    "reach_mi": reach_for(city["density"]),
                    "density": city["density"],
                    "city_keys": [],
                },
            )
            best_dist = 0.0

        city["metro_key"] = best_key
        city["metro_distance_mi"] = round(best_dist, 1)
        metros[best_key]["city_keys"].append(city["key"])

    # Cities with no coordinates fall back to a same-state metro so they still
    # inherit statewide and area coupons.
    for city in cities.values():
        if city.get("metro_key"):
            continue
        same_state = [
            m for m in metros.values() if m["anchor_state"] == city["state"]
        ]
        if same_state:
            fallback = max(
                same_state, key=lambda m: len(m["city_keys"])
            )
            city["metro_key"] = fallback["key"]
            city["metro_distance_mi"] = None
            fallback["city_keys"].append(city["key"])

    _name_metros(metros, cities)
    return metros


def build_place_coords(cities: dict[str, dict]) -> dict[str, tuple[float, float]]:
    """Coordinates for every named place we can locate, keyed 'normalized|ST'.

    Salon-derived centroids first, then the hand-entered METRO_CENTERS for the
    urban cores Great Clips does not operate in.
    """
    coords: dict[str, tuple[float, float]] = {}
    for spec, latlng in METRO_CENTERS.items():
        name, _, state = spec.rpartition(",")
        coords[f"{normalize_city(name)}|{state.strip()}"] = latlng
    for city in cities.values():  # real salon data wins over the fallback table
        if city["lat"] is not None:
            coords[f"{normalize_city(city['city'])}|{city['state']}"] = (
                city["lat"],
                city["lng"],
            )
    return coords


def _place_id(spec: str) -> str:
    name, _, state = spec.rpartition(",")
    return f"{normalize_city(name)}|{state.strip()}"


def _pick_market_name(
    metro: dict,
    members: list[dict],
    coords: dict[str, tuple[float, float]],
    owner: dict[str, str],
) -> str:
    """Highest-ranked principal city within the anchor's reach, else biggest member.

    A city that belongs to a *different* market can never lend its name, which is
    what keeps the market around Carson City from also calling itself "Reno" just
    because Reno sits 30 miles up the road. Cities with no salons at all belong to
    no market, so Detroit and Philadelphia stay available as names.
    """
    reach = max(metro["reach_mi"], 20.0)

    lead_spec = None
    for spec in PRINCIPAL_CITIES:
        pid = _place_id(spec)
        latlng = coords.get(pid)
        if not latlng:
            continue
        held_by = owner.get(pid)
        if held_by is not None and held_by != metro["key"]:
            continue
        if haversine_mi(metro["lat"], metro["lng"], latlng[0], latlng[1]) <= reach:
            lead_spec = spec
            break

    if lead_spec is None:
        return members[0]["city"] if members else metro["anchor_city"]

    lead_name = lead_spec.rpartition(",")[0]
    lead_id = _place_id(lead_spec)

    # Upgrade to a twin name when both halves sit inside this market.
    for first, second in TWIN_MARKETS:
        ids = (_place_id(first), _place_id(second))
        if lead_id not in ids:
            continue
        both_in_range = all(
            (pid in coords)
            and owner.get(pid, metro["key"]) == metro["key"]
            and haversine_mi(
                metro["lat"], metro["lng"], coords[pid][0], coords[pid][1]
            )
            <= reach
            for pid in ids
        )
        if both_in_range:
            return f"{first.rpartition(',')[0]}-{second.rpartition(',')[0]}"

    # Prefer the member city's own spelling so the name matches its page.
    for member in members:
        if f"{normalize_city(member['city'])}|{member['state']}" == lead_id:
            return member["city"]
    return lead_name


def _name_metros(metros: dict[str, dict], cities: dict[str, dict]) -> None:
    """Give each metro a display name, salon/city totals and state list."""
    city_coords = build_place_coords(cities)
    owner = {
        f"{normalize_city(c['city'])}|{c['state']}": c["metro_key"]
        for c in cities.values()
        if c.get("metro_key")
    }

    for metro in metros.values():
        members = [cities[k] for k in metro["city_keys"]]
        members.sort(key=lambda c: (-c["salon_count"], c["city"]))

        metro["salon_count"] = sum(c["salon_count"] for c in members)
        metro["city_count"] = len(members)
        metro["states"] = sorted({c["state"] for c in members})

        # Name the market after the most prominent city in range of the anchor.
        # The anchor is a density centroid and usually a suburb, so it makes a
        # poor label. Range is tested against the anchor's own reach, and the
        # candidate need not have a salon - that is what lets the Michigan market
        # be called Detroit rather than Warren.
        name = _pick_market_name(metro, members, city_coords, owner)
        metro["name"] = name
        metro["name_city_key"] = next(
            (
                c["key"]
                for c in members
                if normalize_city(c["city"]) == normalize_city(name.split("-")[0])
            ),
            metro["key"],
        )
        metro["city_keys"] = [c["key"] for c in members]

    _dedupe_market_names(metros, cities, city_coords)

    for metro in metros.values():
        # If the market is named after a city in a state none of its salons are in
        # - the salons nearest New York City are all in New Jersey - say "area" so
        # "New York Area, NJ" does not read as a mistake.
        lead_state = next(
            (
                spec.rpartition(",")[2].strip()
                for spec in PRINCIPAL_CITIES
                if spec.rpartition(",")[0] == metro["name"].split("-")[0]
            ),
            None,
        )
        label = metro["name"]
        if lead_state and lead_state not in metro["states"]:
            label = f"{metro['name']} Area"
        metro["display_name"] = f"{label}, {'/'.join(metro['states'])}"


def _dedupe_market_names(
    metros: dict[str, dict], cities: dict[str, dict], coords: dict
) -> None:
    """Ensure no two markets share a name.

    Salon-free centres belong to no market, so two neighbouring clusters can both
    reach for the same label - the two clusters flanking Worcester both wanted to
    be "Worcester". The nearer anchor keeps the name; the other falls back to its
    own largest city.
    """
    by_name: dict[str, list[dict]] = {}
    for metro in metros.values():
        by_name.setdefault(metro["name"], []).append(metro)

    taken = {name for name, group in by_name.items() if len(group) == 1}

    for name, group in by_name.items():
        if len(group) == 1:
            continue

        latlng = coords.get(_place_id(f"{name}, {group[0]['anchor_state']}"))
        if latlng:
            group.sort(
                key=lambda m: haversine_mi(m["lat"], m["lng"], latlng[0], latlng[1])
            )
        else:
            group.sort(key=lambda m: -m["salon_count"])

        group[0]["name"] = name
        taken.add(name)

        for loser in group[1:]:
            members = [cities[k] for k in loser["city_keys"]]
            anchor = loser["anchor_city"]
            options = (
                [c["city"] for c in members]
                + [anchor]
                + [f"{anchor}-{c['city']}" for c in members if c["city"] != anchor]
            )
            fallback = next((o for o in options if o not in taken), None)
            if fallback is None:
                fallback, suffix = f"{anchor} Area", 2
                while fallback in taken:
                    fallback = f"{anchor} Area {suffix}"
                    suffix += 1
            loser["name"] = fallback
            taken.add(fallback)


# ------------------------------------------------- coupon area resolution ----

def build_city_lookup(cities: dict[str, dict]) -> dict[str, list[dict]]:
    """Normalized city name -> city records (several states can share a name)."""
    lookup: dict[str, list[dict]] = {}
    for city in cities.values():
        lookup.setdefault(normalize_city(city["city"]), []).append(city)
    return lookup


def _candidate_tokens(area: str) -> list[str]:
    """Break a market string into the place names it might contain."""
    cleaned = AREA_NOISE.sub(" ", area or "")
    cleaned = re.sub(r"\s+", " ", cleaned).strip(" ,-&/")
    if not cleaned:
        return []

    tokens: list[str] = [cleaned]
    # Great Clips market names are delimited a few different ways:
    #   "Reno, Carson City & West NV"
    #   "Calgary-Lethbridge-Airdrie-Okotoks-Cochrane"
    for part in re.split(r"[,&/]| \+ |\band\b", cleaned, flags=re.I):
        part = part.strip(" -")
        if part:
            tokens.append(part)
            if "-" in part:
                tokens.extend(p.strip() for p in part.split("-") if p.strip())
    seen, out = set(), []
    for t in tokens:
        n = normalize_city(t)
        if n and n not in seen and len(n) > 2:
            seen.add(n)
            out.append(t.strip())
    return out


def _state_code_list(area: str) -> list[str]:
    """State codes if the market string is nothing but a list of states.

    "participating NJ, PA & DE" -> ["NJ", "PA", "DE"]; anything naming a city
    returns [] so it goes through normal market resolution instead.
    """
    cleaned = AREA_NOISE.sub(" ", area or "")
    parts = [p.strip(" .-") for p in re.split(r"[,&/]|\band\b", cleaned, flags=re.I)]
    parts = [p for p in parts if p]
    if not parts:
        return []

    codes = []
    for part in parts:
        token = part.upper().replace(".", "").strip()
        if token in STATE_NAMES:
            codes.append(token)
        else:
            return []
    # De-duplicate, preserving order.
    return list(dict.fromkeys(codes))


def resolve_area(
    area: str,
    cities: dict[str, dict],
    lookup: dict[str, list[dict]],
    state_hint: str | None = None,
) -> dict:
    """Map a coupon market string to metro keys and the cities they cover.

    Returns {"metro_keys": [...], "matched": [...], "unmatched": [...]}.
    """
    metro_keys: list[str] = []
    matched: list[str] = []
    unmatched: list[str] = []

    def add_city(city: dict) -> None:
        mk = city.get("metro_key")
        if mk and mk not in metro_keys:
            metro_keys.append(mk)

    def apply_alias(alias_key: str) -> bool:
        hit = False
        for spec in AREA_ALIASES[alias_key]:
            city_name, _, st = spec.rpartition(",")
            st = st.strip()
            for cand in lookup.get(normalize_city(city_name), []):
                if cand["state"] == st:
                    add_city(cand)
                    hit = True
            if not hit:  # alias points at a city with no salons of its own
                hit = _add_metro_near_center(normalize_city(city_name), st, metro_keys)
        return hit

    def resolve_name(name: str, hint: str | None) -> bool:
        """Resolve one place name to a metro. True if something matched."""
        norm = normalize_city(name)

        if norm in AREA_ALIASES and apply_alias(norm):
            return True

        # Market strings pad the nickname with extra words ("DFW Metroplex",
        # "Chicagoland Suburbs"). Try the longest alias contained in the string.
        contained = sorted(
            (
                key
                for key in AREA_ALIASES
                if re.search(rf"\b{re.escape(key)}\b", norm)
            ),
            key=len,
            reverse=True,
        )
        for key in contained:
            if apply_alias(key):
                return True

        candidates = lookup.get(norm, [])
        if candidates:
            if hint:
                in_state = [c for c in candidates if c["state"] == hint]
                if in_state:
                    for c in in_state:
                        add_city(c)
                    return True
                # Same name, wrong state. Do NOT settle for it - there is a Newark
                # in DE, OH and NJ, and picking the largest would advertise a New
                # Jersey coupon in Ohio. Fall through to the metro-centre lookup,
                # which stays inside the hinted state.
            else:
                # Genuinely ambiguous: take the biggest market carrying the name.
                add_city(max(candidates, key=lambda c: c["salon_count"]))
                return True

        # No salon city by that name. It may still be a real metro centre that
        # Great Clips skips - "Detroit", "Philadelphia", "Boston". Fall back to
        # the nearest market anchor around that point.
        return _add_metro_near_center(norm, hint, metro_keys)

    if FOREIGN_MARKERS.search(area or ""):
        return {
            "metro_keys": [],
            "matched": [],
            "unmatched": [area],
            "rejected": "foreign_market",
        }

    tokens = _candidate_tokens(area)
    for token in tokens:
        # A trailing state code scopes the token: "West NV" -> NV.
        hint = state_hint
        st_match = re.search(r"\b([A-Z]{2})$", token.strip())
        if st_match and st_match.group(1) in STATE_NAMES:
            hint = st_match.group(1)
            token = token[: st_match.start()].strip(" ,-")
            if not token:
                continue

        if resolve_name(token, hint):
            matched.append(token)
        else:
            unmatched.append(token)

    # Real market names routinely pair one city with region descriptors that will
    # never match a city - "Jacksonville, NE Florida & SE Georgia". Rejecting those
    # would drop a coupon we understand perfectly well, so only bail out when a
    # lone match is surrounded by many misses, which is the shape of a foreign or
    # garbled market rather than a US one.
    if not matched:
        return {
            "metro_keys": [],
            "matched": matched,
            "unmatched": unmatched,
            "rejected": "no_match",
        }
    if len(matched) <= 1 and len(unmatched) >= 5:
        return {
            "metro_keys": [],
            "matched": matched,
            "unmatched": unmatched,
            "rejected": "low_confidence",
        }

    return {"metro_keys": metro_keys, "matched": matched, "unmatched": unmatched}


def coupon_market_keys(
    coupon: dict,
    cities: dict[str, dict],
    lookup: dict[str, list[dict]],
) -> dict:
    """Classify one coupon and list the metros / cities it reaches.

    scope is one of: national, area, state, salon, unknown.
    """
    state = (coupon.get("state") or "").strip().upper()
    area_name = coupon.get("area_name") or ""
    market = coupon.get("market") or ""
    city = (coupon.get("city") or "").strip().rstrip(",")

    blob = f"{area_name} {market} {coupon.get('location_name') or ''}".lower()
    if state == "US" or re.search(r"\bparticipating us\b|\bus area\b", blob):
        return {"scope": "national", "metro_keys": [], "city_keys": []}

    # Salon-specific: a real city and street address came off the coupon.
    if city and coupon.get("address") and state in STATE_NAMES:
        key = f"{state}/{slugify(city)}"
        if key in cities:
            return {"scope": "salon", "metro_keys": [], "city_keys": [key]}

    if state in STATE_NAMES and not area_name:
        return {
            "scope": "state",
            "metro_keys": [],
            "city_keys": [],
            "state": state,
            "states": [state],
        }

    source = area_name or market

    # Some markets are a plain list of states - "participating NJ, PA & DE". There
    # is no city to resolve, so treat it as statewide across each one.
    states = _state_code_list(source)
    if states:
        return {
            "scope": "state",
            "metro_keys": [],
            "city_keys": [],
            "state": states[0],
            "states": states,
        }

    if source:
        hint = state if state in STATE_NAMES else None
        resolved = resolve_area(source, cities, lookup, hint)
        if resolved["metro_keys"]:
            city_keys = [
                ck
                for mk in resolved["metro_keys"]
                for ck in _metro_city_keys(mk)
            ]
            return {
                "scope": "area",
                "metro_keys": resolved["metro_keys"],
                "city_keys": city_keys,
                "unmatched": resolved["unmatched"],
            }

    return {"scope": "unknown", "metro_keys": [], "city_keys": []}


_METRO_INDEX: dict[str, list[str]] = {}
_METRO_POINTS: list[dict] = []

# How far from a named metro centre we will still accept a market as "that city's
# market" when the centre itself has no salons.
CENTER_MATCH_MI = 40.0


def _metro_city_keys(metro_key: str) -> list[str]:
    return _METRO_INDEX.get(metro_key, [])


def set_metro_index(metros: dict[str, dict]) -> None:
    """Register metros so coupon_market_keys() can expand them to cities."""
    _METRO_INDEX.clear()
    _METRO_POINTS.clear()
    for key, metro in metros.items():
        _METRO_INDEX[key] = list(metro["city_keys"])
        _METRO_POINTS.append(
            {
                "key": key,
                "lat": metro["lat"],
                "lng": metro["lng"],
                "salon_count": metro.get("salon_count", 0),
                "state": metro["anchor_state"],
            }
        )


def _add_metro_near_center(
    norm_name: str, state_hint: str | None, metro_keys: list[str]
) -> bool:
    """Match a salon-free metro centre (e.g. Detroit) to its surrounding market."""
    candidates = [
        (spec, latlng)
        for spec, latlng in METRO_CENTERS.items()
        if normalize_city(spec.rpartition(",")[0]) == norm_name
        and (state_hint is None or spec.rpartition(",")[2].strip() == state_hint)
    ]
    if not candidates or not _METRO_POINTS:
        return False

    hit = False
    for _spec, (lat, lng) in candidates:
        nearby = [
            (haversine_mi(lat, lng, m["lat"], m["lng"]), m) for m in _METRO_POINTS
        ]
        nearby = [(d, m) for d, m in nearby if d <= CENTER_MATCH_MI]
        if not nearby:
            continue
        # Prefer the biggest market around that point, not merely the closest -
        # downtown Detroit is ringed by several anchors.
        best = max(nearby, key=lambda pair: (pair[1]["salon_count"], -pair[0]))[1]
        if best["key"] not in metro_keys:
            metro_keys.append(best["key"])
        hit = True
    return hit


# -------------------------------------------------------------- build/save ---

def build_all(salons_path: Path = SALONS_FILE) -> tuple[dict, dict]:
    salons = load_salons(salons_path)
    cities = build_cities(salons)
    metros = build_metros(cities)
    set_metro_index(metros)
    return cities, metros


def nearest_cities(
    city: dict, cities: dict[str, dict], limit: int = 8, max_mi: float = 45.0
) -> list[dict]:
    """Closest other cities with a salon, nearest first."""
    if city["lat"] is None:
        same_state = [
            c
            for c in cities.values()
            if c["state"] == city["state"] and c["key"] != city["key"]
        ]
        same_state.sort(key=lambda c: -c["salon_count"])
        return [{"city": c, "distance_mi": None} for c in same_state[:limit]]

    out = []
    for other in cities.values():
        if other["key"] == city["key"] or other["lat"] is None:
            continue
        d = haversine_mi(city["lat"], city["lng"], other["lat"], other["lng"])
        if d <= max_mi:
            out.append({"city": other, "distance_mi": round(d, 1)})
    out.sort(key=lambda r: r["distance_mi"])
    return out[:limit]


def save_metros(cities: dict, metros: dict, path: Path = METROS_FILE) -> None:
    """Persist a compact view of the market model for other scripts to read."""
    payload = {
        "total_cities": len(cities),
        "total_metros": len(metros),
        "metros": {
            k: {
                "name": m["name"],
                "display_name": m["display_name"],
                "anchor_city": m["anchor_city"],
                "anchor_state": m["anchor_state"],
                "states": m["states"],
                "salon_count": m["salon_count"],
                "city_count": m["city_count"],
                "reach_mi": m["reach_mi"],
                "city_keys": m["city_keys"],
            }
            for k, m in sorted(metros.items())
        },
        "cities": {
            k: {
                "city": c["city"],
                "state": c["state"],
                "slug": c["slug"],
                "salon_count": c["salon_count"],
                "metro_key": c.get("metro_key"),
                "lat": c["lat"],
                "lng": c["lng"],
            }
            for k, c in sorted(cities.items())
        },
    }
    with path.open("w", encoding="utf-8") as fh:
        json.dump(payload, fh, indent=1, ensure_ascii=False)


if __name__ == "__main__":
    cities, metros = build_all()
    save_metros(cities, metros)

    print(f"cities : {len(cities):,}")
    print(f"metros : {len(metros):,}")
    print()
    print("Largest markets:")
    for m in sorted(metros.values(), key=lambda m: -m["salon_count"])[:15]:
        print(
            f"  {m['display_name']:<34} {m['salon_count']:>4} salons "
            f"across {m['city_count']:>3} cities (reach {m['reach_mi']:.0f} mi)"
        )
