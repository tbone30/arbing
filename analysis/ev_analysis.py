import csv
import os
from datetime import datetime
from collections import defaultdict

def calculate_implied_probability(odds):
    return 1 / float(odds)

def calculate_ev(odds, true_probability):
    return (true_probability * (odds - 1)) - (1 - true_probability)

def analyze_odds(filename):
    games = defaultdict(lambda: defaultdict(lambda: defaultdict(list)))
    positive_ev_bets = []

    with open(filename, mode='r', encoding='utf-8') as file:
        csv_reader = csv.DictReader(file)
        
        for row in csv_reader:
            sport = row['Sport']
            game_key = f"{row['Home Team']} vs {row['Away Team']}"
            home_odds = float(row['Home Odds'])
            away_odds = float(row['Away Odds'])
            
            games[sport][game_key]['home'].append({
                'Team': row['Home Team'],
                'Opponent': row['Away Team'],
                'Bookmaker': row['Bookmaker'],
                'Odds': home_odds,
                'Implied Probability': calculate_implied_probability(home_odds)
            })
            
            games[sport][game_key]['away'].append({
                'Team': row['Away Team'],
                'Opponent': row['Home Team'],
                'Bookmaker': row['Bookmaker'],
                'Odds': away_odds,
                'Implied Probability': calculate_implied_probability(away_odds)
            })

    for sport, sport_games in games.items():
        for game, data in sport_games.items():
            # Find best odds for each team
            best_home = max(data['home'], key=lambda x: x['Odds'])
            best_away = max(data['away'], key=lambda x: x['Odds'])
            
            # Calculate estimated true probabilities
            total_implied_prob = best_home['Implied Probability'] + best_away['Implied Probability']
            home_true_prob = best_home['Implied Probability'] / total_implied_prob
            away_true_prob = best_away['Implied Probability'] / total_implied_prob
            
            # Calculate EV for each bookmaker's odds
            for team in ['home', 'away']:
                true_prob = home_true_prob if team == 'home' else away_true_prob
                for bet in data[team]:
                    bet['Sport'] = sport
                    bet['Estimated True Probability'] = true_prob
                    bet['EV'] = calculate_ev(bet['Odds'], true_prob)
                    if bet['EV'] > 0:
                        positive_ev_bets.append(bet)

    return positive_ev_bets, games

def main(filename):
    positive_ev_bets, all_games = analyze_odds(filename)
    
    os.makedirs('logs', exist_ok=True)
    log_filename = f"logs/analysis_log_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
    
    with open(log_filename, 'w') as log_file:
        log_file.write("Analysis Results:\n\n")
        
        log_file.write("All Analyzed Games:\n")
        for sport, sport_games in all_games.items():
            log_file.write(f"\n{sport.upper()}:\n")
            for game, data in sport_games.items():
                log_file.write(f"{game}:\n")
                for team in ['home', 'away']:
                    log_file.write(f"  {data[team][0]['Team']}:\n")
                    for bet in data[team]:
                        log_file.write(f"    {bet['Bookmaker']}:\n")
                        log_file.write(f"      Odds: {bet['Odds']:.2f}\n")
                        log_file.write(f"      Implied Probability: {bet['Implied Probability']:.2%}\n")
                        log_file.write(f"      Estimated True Probability: {bet['Estimated True Probability']:.2%}\n")
                        log_file.write(f"      EV: {bet['EV']:.2%}\n")
                log_file.write("\n")
        
        log_file.write("\nPositive EV Bet Opportunities:\n")
        if positive_ev_bets:
            for bet in sorted(positive_ev_bets, key=lambda x: x['EV'], reverse=True):
                log_file.write(f"{bet['Sport']} - {bet['Team']} vs {bet['Opponent']} - {bet['Bookmaker']}:\n")
                log_file.write(f"  Odds: {bet['Odds']:.2f}\n")
                log_file.write(f"  Implied Probability: {bet['Implied Probability']:.2%}\n")
                log_file.write(f"  Estimated True Probability: {bet['Estimated True Probability']:.2%}\n")
                log_file.write(f"  EV: {bet['EV']:.2%}\n\n")
        else:
            log_file.write("No positive EV bet opportunities found.\n")
    
    print(f"Analysis results have been saved to {log_filename}")
    return log_filename

if __name__ == "__main__":
    main('path_to_your_csv_file.csv')