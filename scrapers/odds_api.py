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
    "basketball_nba",
    "soccer_epl",
    "baseball_mlb",
    "icehockey_nhl"
]

params = {
    "api_key": os.getenv("API_KEY"),  # Get API key from environment variable
    "regions": "us,uk",
    "markets": "h2h",
    "oddsFormat": "decimal",
    "dateFormat": "iso"
}

def fetch_odds(sport):
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
        writer.writerow(["Sport", "Home Team", "Away Team", "Start Time", "Bookmaker", "Home Odds", "Away Odds"])

        for sport, data in all_data.items():
            for event in data:
                home_team = event['home_team']
                away_team = event['away_team']
                start_time = event['commence_time']

                for bookmaker in event['bookmakers']:
                    market = next((m for m in bookmaker['markets'] if m['key'] == 'h2h'), None)
                    if market:
                        odds = {o['name']: o['price'] for o in market['outcomes']}
                        writer.writerow([
                            sport,
                            home_team,
                            away_team,
                            start_time,
                            bookmaker['title'],
                            odds.get(home_team, 'N/A'),
                            odds.get(away_team, 'N/A')
                        ])
    
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