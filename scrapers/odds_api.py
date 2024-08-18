import requests
import csv
from datetime import datetime
import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

BASE_URL = "https://api.the-odds-api.com/v4/sports"

SPORTS = [
    "americanfootball_nfl",
    "baseball_mlb",
    "soccer_epl",
    # "soccer_la_liga",
    # "basketball_nba",
    # "soccer_mls",
    # "icehockey_nhl",
]

# Configuration
MARKETS = {
    'default': ['h2h'],
    'americanfootball_nfl': ['h2h', 'spreads', 'totals'],
    'baseball_mlb': ['h2h', 'totals'],
    'soccer_epl': ['h2h', 'spreads', 'totals'],
    'soccer_la_liga': ['h2h', 'spreads', 'totals'],
}
REGIONS = ['us']

def fetch_odds(sport):
    params = {
        "api_key": os.getenv("API_KEY"),
        "regions": ','.join(REGIONS),
        "markets": ','.join(MARKETS.get(sport, MARKETS['default'])),
        "oddsFormat": "decimal",
        "dateFormat": "iso"
    }
    
    url = f"{BASE_URL}/{sport}/odds"
    response = requests.get(url, params=params)
    if response.status_code != 200:
        print(f"Failed to get odds for {sport}: status_code {response.status_code}, response body {response.text}")
        return None
    return response.json()

def save_to_csv(all_data):
    if not all_data:
        print("No data to save")
        return None

    os.makedirs('data', exist_ok=True)
    filename = f"data/all_sports_odds_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
    
    with open(filename, mode='w', newline='', encoding='utf-8') as file:
        writer = csv.writer(file)
        
        headers = ["Sport", "Home Team", "Away Team", "Start Time", "Bookmaker", 
                   "Home Odds", "Away Odds", "Draw Odds",
                   "Home Spread", "Home Spread Odds", "Away Spread", "Away Spread Odds", 
                   "Over", "Over Odds", "Under", "Under Odds"]
        
        writer.writerow(headers)

        for sport, data in all_data.items():
            for event in data:
                home_team = event['home_team']
                away_team = event['away_team']
                start_time = event['commence_time']

                for bookmaker in event['bookmakers']:
                    row = [sport, home_team, away_team, start_time, bookmaker['title']]
                    
                    # Initialize all odds fields with 'N/A'
                    odds_fields = ['N/A'] * 11
                    
                    for market in bookmaker['markets']:
                        if market['key'] == 'h2h':
                            odds = {o['name']: o['price'] for o in market['outcomes']}
                            odds_fields[0] = odds.get(home_team, 'N/A')
                            odds_fields[1] = odds.get(away_team, 'N/A')
                            odds_fields[2] = odds.get('Draw', 'N/A')  # Add draw odds
                        elif market['key'] == 'spreads':
                            for outcome in market['outcomes']:
                                if outcome['name'] == home_team:
                                    odds_fields[3] = outcome.get('point', 'N/A')
                                    odds_fields[4] = outcome['price']
                                else:
                                    odds_fields[5] = outcome.get('point', 'N/A')
                                    odds_fields[6] = outcome['price']
                        elif market['key'] == 'totals':
                            odds_fields[7] = market.get('total', 'N/A')
                            for outcome in market['outcomes']:
                                if outcome['name'] == 'Over':
                                    odds_fields[8] = outcome['price']
                                else:
                                    odds_fields[10] = outcome['price']
                    
                    row.extend(odds_fields)
                    writer.writerow(row)
    
    print(f"Data for all sports saved to {filename}")
    return filename

def main():
    all_data = {}
    for sport in SPORTS:
        print(f"Fetching odds data for {sport}...")
        odds_data = fetch_odds(sport)
        if odds_data:
            all_data[sport] = odds_data
    
    if all_data:
        filename = save_to_csv(all_data)
        return filename
    return None

if __name__ == "__main__":
    main()