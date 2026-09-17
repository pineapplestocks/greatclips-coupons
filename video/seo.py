"""Search metadata grounded in the episode's verified offers and actual scenes."""
from datetime import date

from video.planner import SITE


def metadata(plan, timeline):
    offers = plan.get('offers', [])
    location = plan.get('location')
    month = date.fromisoformat(plan['date']).strftime('%b %Y')
    tags = ['Great Clips coupons', 'Great Clips haircut coupons', 'GreatClipsDeal']
    if offers:
        labels = {o['label'] for o in offers}
        label = next(iter(labels)) if len(labels) == 1 else 'Local Haircut Deals'
        where = f' in {location}' if location else ''
        title = f'Great Clips Coupons{where}: {label} ({month})'
        intro = (f'Looking for Great Clips coupons{where}? Featured offer: '
                 f'{label.lower()}. Valid only at the participating locations listed below. '
                 f'Offers checked {plan["date"]}; availability can change.')
        tags += [f'Great Clips coupons {location}', f'{location} haircut coupons'] if location else ['local haircut coupons']
        tags += [f'Great Clips {label.lower()}', f'Great Clips coupons {month}']
    else:
        title = 'Great Clips Coupons: How to Find & Use Local Haircut Deals'
        intro = ('Find Great Clips coupons near you and learn how to use them. '
                 'This quick guide explains location searches, coupon wording, '
                 'expiration dates, email delivery, and showing your offer at the salon.')
        tags += ['Great Clips coupons near me', 'how to use Great Clips coupons', 'Great Clips coupon guide']
    # Keep long area names from creating invalid API titles.
    if len(title) > 100:
        title = f'Great Clips Coupons{where}: {label}'
    title = title[:100].rstrip()
    link = f'{SITE}/?utm_source=youtube&utm_medium=video&utm_campaign={plan["id"]}'
    lines = [intro, f'Find local coupon listings and request your coupon link: {link}', '']
    if offers:
        lines += ['FEATURED OFFERS — check your exact salon and expiration:']
        for offer in offers:
            place = (f'{offer["address"]}, {offer["location"]}' if offer.get('address')
                     else f'Participating {offer["location"]} area salons')
            lines += [f'{place}: {offer["label"]}. Expires {offer["expiration"]}.',
                      f'Official coupon and full restrictions: {offer["url"]}']
        lines += ['These are local offers, not nationwide prices. Follow each official coupon\'s restrictions; taxes may apply.', '']
    else:
        lines += ['The prices used to explain coupon wording are examples, not live offers.', '']
    # Use real scene starts. Require YouTube's minimum three ten-second chapters.
    chapter_rows = []
    end = max((row['start'] + row.get('duration', 0) for row in timeline), default=0)
    names = {'intro': 'Great Clips coupon overview', 'promise': 'How to find a local offer',
             'search': 'Search coupons near your salon', 'compare': 'Discount versus haircut price',
             'price': 'Read the coupon amount', 'check': 'Check salon participation and expiration',
             'email': 'Get the official coupon link by email', 'redeem': 'Show your coupon at checkout',
             'outro': 'Find more local coupon listings'}
    for index, row in enumerate(timeline):
        start = int(row['start'])
        if chapter_rows and start - chapter_rows[-1][0] < 10:
            continue
        shot = plan['scenes'][index] if index < len(plan['scenes']) else {}
        offer = shot.get('offer')
        name = (f'{offer["location"]}: {offer.get("address") or offer["label"]}' if offer
                else names.get(shot.get('kind'), row['title']))
        chapter_rows.append((start, name))
    while chapter_rows and end - chapter_rows[-1][0] < 10:
        chapter_rows.pop()
    if len(chapter_rows) >= 3 and chapter_rows[0][0] == 0:
        lines += ['CHAPTERS']
        lines += [f'{start//60:02}:{start%60:02} {name}' for start, name in chapter_rows]
        lines += ['']
    lines += ['Coupon requests on GreatClipsDeal use email delivery. Open the official offer from your inbox and follow its redemption instructions.',
              'Subscribe for new local Great Clips coupon guides and verified offer updates.', '',
              'GreatClipsDeal is an independent coupon resource, not affiliated with or endorsed by Great Clips.',
              'Visuals include illustrated website steps and an AI-generated generic salon image. Narration is computer-generated.', '',
              '#GreatClipsCoupons #HaircutCoupons #GreatClips']
    return {'snippet': {'title': title, 'description': '\n'.join(lines),
                        'tags': list(dict.fromkeys(tags)), 'categoryId': '26',
                        'defaultLanguage': 'en', 'defaultAudioLanguage': 'en'}}
