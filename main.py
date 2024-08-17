from scrapers.odds_api import main as fetch_odds
from analysis.ev_analysis import main as analyze_odds

def main():
    # Fetch odds data for all sports
    print("Fetching odds data for all sports...")
    odds_file = fetch_odds()
    
    if odds_file:
        print(f"Odds data saved to {odds_file}")
        
        # Analyze odds data and get betting recommendations
        print("\nAnalyzing odds data and generating betting recommendations...")
        log_file = analyze_odds(odds_file)
        
        print(f"\nAnalysis complete. Detailed recommendations have been saved to {log_file}")
        print("\nBetting Recommendations Summary:")
        
        with open(log_file, 'r') as f:
            content = f.read()
            print(content)
    else:
        print("Failed to fetch odds data. Analysis cannot be performed.")

if __name__ == "__main__":
    main()