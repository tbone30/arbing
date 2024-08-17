import csv
import os
from datetime import datetime, timedelta
from collections import defaultdict
from itertools import combinations
import pytz

# Configuration
MINIMUM_ARBITRAGE_PROFIT = 10  # Minimum profit in dollars for arbitrage opportunities
MAX_DAYS_AHEAD = 7  # Maximum number of days ahead for considering events
MAX_OPPORTUNITIES_PER_GAME = 3  # Maximum number of opportunities to show per game
ALLOWED_BOOKMAKERS = {'betus', 'bet365', 'fanduel', 'draftkings'}  # Set of allowed bookmakers
MIN_EV_THRESHOLD = 0.01  # Minimum EV to consider a bet (1%)
MAX_EV_THRESHOLD = 0.15  # Maximum EV to consider realistic (15%)

# Time zone configuration
EST = pytz.timezone('US/Eastern')

def decimal_to_american(decimal_odds):
    if decimal_odds >= 2:
        return f"+{int((decimal_odds - 1) * 100)}"
    else:
        return f"-{int(100 / (decimal_odds - 1))}"

def american_to_decimal(american_odds):
    if american_odds > 0:
        return 1 + (american_odds / 100)
    else:
        return 1 + (100 / abs(american_odds))

def calculate_implied_probability(odds):
    return 1 / float(odds)

def calculate_ev(odds, true_probability):
    return (true_probability * (odds - 1)) - (1 - true_probability)

def calculate_hedge_bet(stake, odds1, odds2):
    total_stake = stake * (odds1 / odds2)
    return total_stake - stake

def parse_and_convert_to_est(date_string):
    # Assume input is in UTC
    utc_time = datetime.strptime(date_string, "%Y-%m-%dT%H:%M:%SZ")
    utc_time = pytz.utc.localize(utc_time)
    est_time = utc_time.astimezone(EST)
    return est_time

def format_est_time(est_time):
    return est_time.strftime("%m/%d/%Y %I:%M %p EST")

def is_within_time_range(event_time):
    now = datetime.now(EST)
    est_event_time = parse_and_convert_to_est(event_time)
    return now <= est_event_time <= (now + timedelta(days=MAX_DAYS_AHEAD))

def analyze_odds(filename):
    games = defaultdict(lambda: defaultdict(lambda: defaultdict(list)))
    positive_ev_bets = []
    arbitrage_opportunities = []
    hedging_opportunities = []
    game_opportunity_count = defaultdict(int)

    with open(filename, mode='r', encoding='utf-8') as file:
        csv_reader = csv.DictReader(file)
        
        for row in csv_reader:
            sport = row['Sport']
            game_key = f"{row['Home Team']} vs {row['Away Team']}"
            home_odds = float(row['Home Odds'])
            away_odds = float(row['Away Odds'])
            draw_odds = float(row['Draw Odds']) if 'Draw Odds' in row else None
            start_time = row['Start Time']
            bookmaker = row['Bookmaker'].lower()
            
            if not is_within_time_range(start_time) or bookmaker not in ALLOWED_BOOKMAKERS:
                continue
            
            est_start_time = format_est_time(parse_and_convert_to_est(start_time))
            
            games[sport][game_key]['home'].append({
                'Team': row['Home Team'],
                'Opponent': row['Away Team'],
                'Bookmaker': bookmaker,
                'Odds': home_odds,
                'Implied Probability': calculate_implied_probability(home_odds),
                'Start Time': est_start_time
            })
            
            games[sport][game_key]['away'].append({
                'Team': row['Away Team'],
                'Opponent': row['Home Team'],
                'Bookmaker': bookmaker,
                'Odds': away_odds,
                'Implied Probability': calculate_implied_probability(away_odds),
                'Start Time': est_start_time
            })
            
            if draw_odds:
                games[sport][game_key]['draw'].append({
                    'Team': 'Draw',
                    'Bookmaker': bookmaker,
                    'Odds': draw_odds,
                    'Implied Probability': calculate_implied_probability(draw_odds),
                    'Start Time': est_start_time
                })

    for sport, sport_games in games.items():
        for game, data in sport_games.items():
            outcomes = ['home', 'away', 'draw'] if 'draw' in data else ['home', 'away']
            best_odds = {outcome: max(data[outcome], key=lambda x: x['Odds']) for outcome in outcomes}
            
            total_implied_prob = sum(bet['Implied Probability'] for bet in best_odds.values())
            true_probs = {outcome: bet['Implied Probability'] / total_implied_prob for outcome, bet in best_odds.items()}
            
            for outcome in outcomes:
                for bet in data[outcome]:
                    bet['Sport'] = sport
                    bet['Game'] = game
                    bet['Estimated True Probability'] = true_probs[outcome]
                    bet['EV'] = calculate_ev(bet['Odds'], true_probs[outcome])
                    if MIN_EV_THRESHOLD <= bet['EV'] <= MAX_EV_THRESHOLD and game_opportunity_count[game] < MAX_OPPORTUNITIES_PER_GAME:
                        positive_ev_bets.append(bet)
                        game_opportunity_count[game] += 1

            # Check for arbitrage opportunities
            for combo in combinations(outcomes, len(outcomes)):
                arb_bets = [max(data[outcome], key=lambda x: x['Odds']) for outcome in combo]
                total_arb_prob = sum(1 / bet['Odds'] for bet in arb_bets)
                if total_arb_prob < 1 and game_opportunity_count[game] < MAX_OPPORTUNITIES_PER_GAME:
                    stakes = [100 / bet['Odds'] / total_arb_prob for bet in arb_bets]
                    total_stake = sum(stakes)
                    profit = 100 / total_arb_prob - total_stake
                    
                    if profit >= MINIMUM_ARBITRAGE_PROFIT:
                        opportunity = {
                            'Sport': sport,
                            'Game': game,
                            'Bets': list(zip(arb_bets, stakes)),
                            'Profit': profit,
                            'Start Time': arb_bets[0]['Start Time']
                        }
                        arbitrage_opportunities.append(opportunity)
                        game_opportunity_count[game] += 1
                    elif profit > 0:
                        hedging_opportunities.append(opportunity)

    return positive_ev_bets, arbitrage_opportunities, hedging_opportunities, games

def format_bet_recommendation(bet):
    american_odds = decimal_to_american(bet['Odds'])
    return (f"{bet['Sport']} - {bet['Game']} (Start: {bet['Start Time']})\n"
            f"  Bet on: {bet['Team']} @ {bet['Bookmaker']}\n"
            f"  Odds: {bet['Odds']:.2f} (Decimal) / {american_odds} (American)\n"
            f"  Expected Value: {bet['EV']:.2%}\n"
            f"  Estimated True Probability: {bet['Estimated True Probability']:.2%}\n")

def format_arbitrage_opportunity(opp):
    bet_strings = []
    for bet, stake in opp['Bets']:
        american_odds = decimal_to_american(bet['Odds'])
        bet_strings.append(f"  Bet {len(bet_strings)+1}: {bet['Team']} @ {bet['Bookmaker']} - "
                           f"Odds: {bet['Odds']:.2f} (Decimal) / {american_odds} (American), Stake: ${stake:.2f}")
    
    return (f"{opp['Sport']} - {opp['Game']} (ARBITRAGE) (Start: {opp['Start Time']})\n" +
            "\n".join(bet_strings) +
            f"\n  Guaranteed Profit: ${opp['Profit']:.2f}\n")

def main(filename):
    positive_ev_bets, arbitrage_opportunities, hedging_opportunities, games = analyze_odds(filename)
    
    os.makedirs('logs', exist_ok=True)
    log_filename = f"logs/betting_recommendations_{datetime.now(EST).strftime('%Y%m%d_%H%M%S')}.txt"
    
    with open(log_filename, 'w') as log_file:
        log_file.write("Betting Recommendations:\n\n")
        
        log_file.write("Configuration:\n")
        log_file.write(f"Allowed Bookmakers: {', '.join(ALLOWED_BOOKMAKERS)}\n")
        log_file.write(f"Minimum Arbitrage Profit: ${MINIMUM_ARBITRAGE_PROFIT}\n")
        log_file.write(f"Max Days Ahead: {MAX_DAYS_AHEAD}\n")
        log_file.write(f"Max Opportunities Per Game: {MAX_OPPORTUNITIES_PER_GAME}\n")
        log_file.write(f"EV Range: {MIN_EV_THRESHOLD:.2%} to {MAX_EV_THRESHOLD:.2%}\n\n")

        log_file.write("Data Summary:\n")
        for sport, sport_games in games.items():
            log_file.write(f"{sport}:\n")
            for game, data in sport_games.items():
                log_file.write(f"  {game}: {len(data['home'])} home odds, {len(data['away'])} away odds\n")
        log_file.write("\n")

        if positive_ev_bets:
            log_file.write("High Value Single Bets:\n")
            for bet in sorted(positive_ev_bets, key=lambda x: x['EV'], reverse=True)[:10]:  # Top 10 EV bets
                log_file.write(format_bet_recommendation(bet))
            log_file.write("\n")

        if hedging_opportunities:
            log_file.write("Hedging Opportunities:\n")
            for opp in sorted(hedging_opportunities, key=lambda x: x['Profit'], reverse=True)[:5]:  # Top 5 hedging opportunities
                log_file.write(format_arbitrage_opportunity(opp))
            log_file.write("\n")

        if arbitrage_opportunities:
            log_file.write(f"Arbitrage Opportunities (Guaranteed Profit >= ${MINIMUM_ARBITRAGE_PROFIT}, within next {MAX_DAYS_AHEAD} days):\n")
            for opp in sorted(arbitrage_opportunities, key=lambda x: x['Profit'], reverse=True):
                log_file.write(format_arbitrage_opportunity(opp))
            log_file.write("\n")

        # Summary at the bottom
        log_file.write("Betting Strategy Summary:\n")
        log_file.write(f"- High Value Single Bets: {len(positive_ev_bets)}\n")
        log_file.write(f"- Hedging Opportunities: {len(hedging_opportunities)}\n")
        log_file.write(f"- Arbitrage Opportunities (Profit >= ${MINIMUM_ARBITRAGE_PROFIT}, within {MAX_DAYS_AHEAD} days): {len(arbitrage_opportunities)}\n")

    print(f"Betting recommendations have been saved to {log_filename}")
    
    # Print the summary to the console at the bottom
    with open(log_filename, 'r') as log_file:
        content = log_file.read()
        print(content)
    
    return log_filename

if __name__ == "__main__":
    main('path_to_your_csv_file.csv')