from datetime import datetime, timedelta
import json
import os
import time

import pandas as pd
from pytz import timezone
import requests

RESY_API_KEY = os.environ.get("RESY_API_KEY")
NUM_SEATS = '2'
EST_TIMEZONE = timezone('EST')

# list of restaurants to check, uncomment or add below
restaurants = [
    {'url_slug':'4-charles-prime-rib','city':'ny','venue_id':'834','source':'resy'},
    {'url_slug':'the-polo-bar','city':'ny','venue_id':'6439','source':'resy'},
    {'url_slug':'nami-nori','city':'ny','venue_id':'7425','source':'resy'},
    {'url_slug':'minetta-tavern','city':'ny','venue_id':'9846','source':'resy'},
    {'url_slug':'lilia','city':'ny','venue_id':'418','source':'resy'},
    # {'url_slug':'her-name-is-han','city':'ny','venue_id':'1010','source':'resy'},
    # {'url_slug':'lartusi-ny','city':'ny','venue_id':'25973','source':'resy'},
    # {'url_slug':'joseph-leonard','city':'ny','venue_id':'394','source':'resy'},
    # TODO add these and others to list
    # https://resy.com/cities/ny/i-sodi?date=2021-12-26&seats=2
    # https://resy.com/cities/ny/jua?date=2021-12-26&seats=2
    # https://resy.com/cities/ny/minetta-tavern?date=2022-01-03&seats=2
    # https://resy.com/cities/ny/the-grill-ny?date=2021-12-26&seats=2
    # https://resy.com/cities/ny/the-lobster-club?date=2021-12-26&seats=2
    # https://resy.com/cities/ny/sweetbriar?date=2021-12-26&seats=2
]


# helpers for querying Resy
def get_resy_venue_availability(venue_id, start_date, end_date, num_seats='2'):
    """
    Get Resy availability by day for a given venue, date range, and number of seats
    """
    url = 'https://api.resy.com/4/venue/calendar'
    payload = {
        'venue_id': venue_id,
        'num_seats': num_seats,
        'start_date': start_date,
        'end_date': end_date,
    }
    headers = {
        'accept': 'application/json, text/plain, */*',
        'accept-encoding': 'gzip, deflate, br',
        'accept-language': 'en-US,en;q=0.9',
        'authorization': RESY_API_KEY,
        'cache-control': 'no-cache',
        'dnt': '1',
        'origin': 'https://resy.com',
        'pragma': 'no-cache',
        'referer': 'https://resy.com/',
        'sec-ch-ua': '" Not A;Brand";v="99", "Chromium";v="96", "Google Chrome";v="96"',
        'sec-ch-ua-mobile': '?1',
        'sec-ch-ua-platform': '"Android"',
        'sec-fetch-dest': 'empty',
        'sec-fetch-mode': 'cors',
        'sec-fetch-site': 'same-site',
        'user-agent': 'Mozilla/5.0 (Linux; Android 6.0; Nexus 5 Build/MRA58N) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/96.0.4664.93 Mobile Safari/537.36',
        'x-origin': 'https://resy.com',
    }
    r = requests.get(url, headers=headers, params=payload)
    r.raise_for_status()
    return r.json()

def get_available_reservations_resy(day, venue_id, party_size=2):
    """
    Get Resy available reservations for a given day, venue and party size
    """
    url = 'https://api.resy.com/4/find'
    payload = {
        'day': day,
        'lat':'40.7462051', # doesn't seem to matter, used for a distance calc
        'location':'ny', # doesn't seem to matter, used for a distance calc
        'long':'-73.9869566', # doesn't seem to matter, used for a distance calc
        'party_size': party_size,
        'venue_id': venue_id,
        'sort_by':'available',
    }
    headers = {
        'accept': 'application/json, text/plain, */*',
        'accept-encoding': 'gzip, deflate, br',
        'accept-language': 'en-US,en;q=0.9',
        'authorization': RESY_API_KEY,
        'cache-control': 'no-cache',
        'dnt': '1',
        'origin': 'https://resy.com',
        'pragma': 'no-cache',
        'referer': 'https://resy.com/',
        'sec-ch-ua': '" Not A;Brand";v="99", "Chromium";v="96", "Google Chrome";v="96"',
        'sec-ch-ua-mobile': '?1',
        'sec-ch-ua-platform': '"Android"',
        'sec-fetch-dest': 'empty',
        'sec-fetch-mode': 'cors',
        'sec-fetch-site': 'same-site',
        'user-agent': 'Mozilla/5.0 (Linux; Android 6.0; Nexus 5 Build/MRA58N) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/96.0.4664.93 Mobile Safari/537.36',
        'x-origin': 'https://resy.com',
    }
    r = requests.get(url, headers=headers, params=payload)
    r.raise_for_status()
    return r.json()


# first query availability for each restaurant over next 30 days
# we do this so we only query for the specific reservation times on
# days we know a given restaurant has some availability
today_datetime = datetime.now(EST_TIMEZONE)
avail_by_date = []
for r in restaurants:
    if r['source'] != 'resy':
        print(f"{r['url_slug']} not supported")
        continue

    avail = get_resy_venue_availability(
        r['venue_id'],
        today_datetime.strftime('%Y-%m-%d'),
        (today_datetime + timedelta(30)).strftime('%Y-%m-%d'),
        NUM_SEATS,
    )
#     time.sleep(0.5) # respect the api

    for a in avail.get('scheduled', []):
        avail_by_date.append({
            'url_slug':r['url_slug'],
            'venue_id':r['venue_id'],
            'source':r['source'],
            'date':a['date'],
            'event': a['inventory']['event'],
            'reservation': a['inventory']['reservation'],
            'walk-in': a['inventory']['walk-in'],
        })

avail_by_date_df = pd.DataFrame(avail_by_date)

to_check = list(
    avail_by_date_df[avail_by_date_df['reservation']=='available']
    [['venue_id', 'date']]
    .to_records(index=False)
)


# second, we query each venue, date combination where the api
# indicated there are reservations available and save down the data we find
available_reservations = []
for venue_id, date in to_check:
    times = get_available_reservations_resy(date, venue_id, party_size=NUM_SEATS)
#     time.sleep(0.5) # respect the api
    for v in times['results']['venues']:
        name = v['venue']['name']
        resy_venue_id = v['venue']['id']['resy']
        source = 'resy'
        url_slug = v['venue']['url_slug']
        city = v['venue']['location']['code']
        resy_url = (
            f"https://resy.com/cities/{city}/{url_slug}?date={date}&seats={NUM_SEATS}"
        )
        for s in v.get('slots'):
            if s['availability']['id']==3:
                # ^^ based on trial and error, "availability id" = 3 means available
                res_type = s['config']['type']
                res_time = s['date']['start']
                available_reservations.append({
                    'name':name,
                    'venue_id':resy_venue_id,
                    'date':date,
                    'res_time':res_time,
                    'res_type':res_type,
                    'source':source,
                    'url_slug':url_slug,
                    'url':resy_url,
                })

reservations_df = pd.DataFrame(available_reservations)
reservations_df.to_csv('data/reservations_latest.csv', index=False)
