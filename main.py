from scrapers.odds_api import main as fetch_odds
from analysis.ev_analysis import main as analyze_odds

def main():
    # Fetch odds data for all sports
    print("Fetching odds data for all sports...")
    odds_file = fetch_odds()
    
    if odds_file:
        print(f"Odds data saved to {odds_file}")
        
        # Analyze odds data for all sports and sportsbooks
        print("\nAnalyzing odds data for positive EV opportunities across all sports and sportsbooks...")
        log_file = analyze_odds(odds_file)
        
        print(f"\nAnalysis complete. Results have been saved to {log_file}")
        print("\nSummary of positive EV opportunities:")
        
        with open(log_file, 'r') as f:
            content = f.read()
            positive_ev_section = content.split("Positive EV Bet Opportunities:")[1]
            print(positive_ev_section)
    else:
        print("Failed to fetch odds data. Analysis cannot be performed.")

if __name__ == "__main__":
    main()