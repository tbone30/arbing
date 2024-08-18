import csv
import os
from datetime import datetime, timedelta
from collections import defaultdict
import pytz

# Configuration
MINIMUM_ARBITRAGE_PROFIT = 0  # Minimum profit in dollars for arbitrage opportunities
MAX_DAYS_AHEAD = 28  # Maximum number of days ahead for considering events
MAX_OPPORTUNITIES_PER_GAME = 3  # Maximum number of opportunities to show per game
ALLOWED_BOOKMAKERS = {'betus', 'fanduel', 'draftkings', 'pointsbetus', 'wynnbet', 'bovada', 'betmgm', 'espnbet', 'fliff', 'betonlineag', 'betrivers', 'hardrockbet'}  # Set of allowed bookmakers
MIN_EV_THRESHOLD = 0.00  # Minimum EV to consider a bet (1%)
MAX_EV_THRESHOLD = 0.15  # Maximum EV to consider realistic (15%)

# Time zone configuration
EST = pytz.timezone('US/Eastern')

def decimal_to_american(decimal_odds):
    if decimal_odds >= 2:
        return f"+{int((decimal_odds - 1) * 100)}"
    else:
        return f"-{int(100 / (decimal_odds - 1))}"

def calculate_implied_probability(odds):
    return 1 / float(odds)

def calculate_ev(odds, true_probability):
    return (true_probability * (odds - 1)) - (1 - true_probability)

def parse_and_convert_to_est(date_string):
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

def find_arbitrage_opportunities(bets, sport):
    opportunities = []
    for market in ['moneyline', 'spread', 'total']:
        if market in bets:
            # Group bets by date
            bets_by_date = defaultdict(list)
            for bet in bets[market]:
                bet_date = datetime.strptime(bet['Start Time'], "%m/%d/%Y %I:%M %p EST").date()
                bets_by_date[bet_date].append(bet)
            
            # Check for arbitrage opportunities within each date
            for date, date_bets in bets_by_date.items():
                if market == 'total':
                    best_over = max(date_bets, key=lambda x: x['Over Odds'])
                    best_under = max(date_bets, key=lambda x: x['Under Odds'])
                    total_prob = (1 / best_over['Over Odds']) + (1 / best_under['Under Odds'])
                    if total_prob < 1:
                        over_stake = (1 / best_over['Over Odds']) / total_prob
                        under_stake = (1 / best_under['Under Odds']) / total_prob
                        min_stake = min(over_stake, under_stake)
                        over_bet = 100 if over_stake == min_stake else 100 * (over_stake / min_stake)
                        under_bet = 100 if under_stake == min_stake else 100 * (under_stake / min_stake)
                        total_investment = over_bet + under_bet
                        profit = (100 / total_prob) - total_investment
                        profit_percentage = (profit / total_investment) * 100
                        if profit > MINIMUM_ARBITRAGE_PROFIT:
                            opportunities.append({
                                'Market': 'Total',
                                'Date': date.strftime("%m/%d/%Y"),
                                'Bets': [
                                    {'Type': 'Over', 'Odds': best_over['Over Odds'], 'Bookmaker': best_over['Bookmaker'], 'Total': best_over['Total'], 'Stake': over_bet},
                                    {'Type': 'Under', 'Odds': best_under['Under Odds'], 'Bookmaker': best_under['Bookmaker'], 'Total': best_under['Total'], 'Stake': under_bet}
                                ],
                                'Profit': profit_percentage,
                                'Total Investment': total_investment
                            })
                else:
                    best_bets = {}
                    for bet in date_bets:
                        outcome = bet['Team']
                        if outcome not in best_bets or bet['Odds'] > best_bets[outcome]['Odds']:
                            best_bets[outcome] = bet
                    
                    # Check if we have odds for all possible outcomes
                    if sport.lower()[:6] == 'soccer' and market == 'moneyline' and len(best_bets) == 3:
                        total_prob = sum(1 / bet['Odds'] for bet in best_bets.values())
                        if total_prob < 1:
                            stakes = {team: (1 / bet['Odds']) / total_prob for team, bet in best_bets.items()}
                            min_stake = min(stakes.values())
                            normalized_stakes = {team: 100 if stake == min_stake else 100 * (stake / min_stake) for team, stake in stakes.items()}
                            total_investment = sum(normalized_stakes.values())
                            profit = (100 / total_prob) - total_investment
                            profit_percentage = (profit / total_investment) * 100
                            if profit > MINIMUM_ARBITRAGE_PROFIT:
                                opportunities.append({
                                    'Market': market.capitalize(),
                                    'Date': date.strftime("%m/%d/%Y"),
                                    'Bets': [{'Type': team, 'Odds': bet['Odds'], 'Bookmaker': bet['Bookmaker'], 'Stake': normalized_stakes[team]} for team, bet in best_bets.items()],
                                    'Profit': profit_percentage,
                                    'Total Investment': total_investment
                                })
                    elif len(best_bets) == 2:  # For non-soccer sports or other markets
                        total_prob = sum(1 / bet['Odds'] for bet in best_bets.values())
                        if total_prob < 1:
                            stakes = {team: (1 / bet['Odds']) / total_prob for team, bet in best_bets.items()}
                            min_stake = min(stakes.values())
                            normalized_stakes = {team: 100 if stake == min_stake else 100 * (stake / min_stake) for team, stake in stakes.items()}
                            total_investment = sum(normalized_stakes.values())
                            payout = min(normalized_stakes[team] * bet['Odds'] for team, bet in best_bets.items())
                            profit = payout - total_investment
                            profit_percentage = (profit / total_investment) * 100
                            if profit > MINIMUM_ARBITRAGE_PROFIT:
                                opportunities.append({
                                    'Market': market.capitalize(),
                                    'Date': date.strftime("%m/%d/%Y"),
                                    'Bets': [{'Type': team, 'Odds': bet['Odds'], 'Bookmaker': bet['Bookmaker'], 'Stake': normalized_stakes[team]} for team, bet in best_bets.items()],
                                    'Profit': profit_percentage,
                                    'Total Investment': total_investment
                                })
    return opportunities

def analyze_odds(filename):
    games = defaultdict(lambda: defaultdict(lambda: defaultdict(list)))
    positive_ev_bets = []
    arbitrage_opportunities = []

    with open(filename, mode='r', encoding='utf-8') as file:
        csv_reader = csv.DictReader(file)
        
        for row in csv_reader:
            sport = row['Sport']
            game_key = f"{row['Home Team']} vs {row['Away Team']}"
            start_time = row['Start Time']
            bookmaker = row['Bookmaker'].lower()
            
            if not is_within_time_range(start_time) or bookmaker not in ALLOWED_BOOKMAKERS:
                continue
            
            est_start_time = format_est_time(parse_and_convert_to_est(start_time))
            
            # Process moneyline (h2h) bets
            if row['Home Odds'] != 'N/A' and row['Away Odds'] != 'N/A':
                home_odds = float(row['Home Odds'])
                away_odds = float(row['Away Odds'])
                
                games[sport][game_key]['moneyline'].append({
                    'Team': row['Home Team'],
                    'Opponent': row['Away Team'],
                    'Bookmaker': bookmaker,
                    'Odds': home_odds,
                    'Implied Probability': calculate_implied_probability(home_odds),
                    'Start Time': est_start_time,
                    'Bet Type': 'Moneyline'
                })
                
                games[sport][game_key]['moneyline'].append({
                    'Team': row['Away Team'],
                    'Opponent': row['Home Team'],
                    'Bookmaker': bookmaker,
                    'Odds': away_odds,
                    'Implied Probability': calculate_implied_probability(away_odds),
                    'Start Time': est_start_time,
                    'Bet Type': 'Moneyline'
                })
                
                # Add draw bet if available (for soccer)
                if sport.lower()[:6] == 'soccer' and 'Draw Odds' in row and row['Draw Odds'] != 'N/A':
                    draw_odds = float(row['Draw Odds'])
                    games[sport][game_key]['moneyline'].append({
                        'Team': 'Draw',
                        'Bookmaker': bookmaker,
                        'Odds': draw_odds,
                        'Implied Probability': calculate_implied_probability(draw_odds),
                        'Start Time': est_start_time,
                        'Bet Type': 'Moneyline'
                    })
            
            # Process spread bets
            if row['Home Spread'] != 'N/A' and row['Home Spread Odds'] != 'N/A':
                home_spread = float(row['Home Spread'])
                home_spread_odds = float(row['Home Spread Odds'])
                away_spread = -home_spread
                away_spread_odds = float(row['Away Spread Odds'])
                
                games[sport][game_key]['spread'].append({
                    'Team': row['Home Team'],
                    'Opponent': row['Away Team'],
                    'Bookmaker': bookmaker,
                    'Spread': home_spread,
                    'Odds': home_spread_odds,
                    'Implied Probability': calculate_implied_probability(home_spread_odds),
                    'Start Time': est_start_time,
                    'Bet Type': 'Spread'
                })
                
                games[sport][game_key]['spread'].append({
                    'Team': row['Away Team'],
                    'Opponent': row['Home Team'],
                    'Bookmaker': bookmaker,
                    'Spread': away_spread,
                    'Odds': away_spread_odds,
                    'Implied Probability': calculate_implied_probability(away_spread_odds),
                    'Start Time': est_start_time,
                    'Bet Type': 'Spread'
                })
            
            # Process total (over/under) bets
            if row['Over'] != 'N/A' and row['Over Odds'] != 'N/A' and row['Under Odds'] != 'N/A':
                total = float(row['Over'])
                over_odds = float(row['Over Odds'])
                under_odds = float(row['Under Odds'])
                
                games[sport][game_key]['total'].append({
                    'Total': total,
                    'Bookmaker': bookmaker,
                    'Over Odds': over_odds,
                    'Under Odds': under_odds,
                    'Over Implied Probability': calculate_implied_probability(over_odds),
                    'Under Implied Probability': calculate_implied_probability(under_odds),
                    'Start Time': est_start_time,
                    'Bet Type': 'Total'
                })

    for sport, sport_games in games.items():
        for game, data in sport_games.items():
            arbitrage_opportunities.extend(find_arbitrage_opportunities(data, sport))
            
            for market in ['moneyline', 'spread', 'total']:
                if market in data:
                    if market == 'total':
                        best_odds = max(data[market], key=lambda x: max(x['Over Odds'], x['Under Odds']))
                        total_implied_prob = best_odds['Over Implied Probability'] + best_odds['Under Implied Probability']
                        true_prob_over = best_odds['Over Implied Probability'] / total_implied_prob
                        true_prob_under = best_odds['Under Implied Probability'] / total_implied_prob
                        
                        ev_over = calculate_ev(best_odds['Over Odds'], true_prob_over)
                        ev_under = calculate_ev(best_odds['Under Odds'], true_prob_under)
                        
                        if MIN_EV_THRESHOLD <= ev_over <= MAX_EV_THRESHOLD:
                            positive_ev_bets.append({
                                'Sport': sport,
                                'Game': game,
                                'Bookmaker': best_odds['Bookmaker'],
                                'Bet Type': 'Total Over',
                                'Total': best_odds['Total'],
                                'Odds': best_odds['Over Odds'],
                                'EV': ev_over,
                                'Start Time': best_odds['Start Time']
                            })
                        
                        if MIN_EV_THRESHOLD <= ev_under <= MAX_EV_THRESHOLD:
                            positive_ev_bets.append({
                                'Sport': sport,
                                'Game': game,
                                'Bookmaker': best_odds['Bookmaker'],
                                'Bet Type': 'Total Under',
                                'Total': best_odds['Total'],
                                'Odds': best_odds['Under Odds'],
                                'EV': ev_under,
                                'Start Time': best_odds['Start Time']
                            })
                    else:
                        if sport.lower()[:6] == 'soccer' and market == 'moneyline':
                            # For soccer moneyline, only consider if all three outcomes are present
                            outcomes = set(bet['Team'] for bet in data[market])
                            if len(outcomes) == 3 and 'Draw' in outcomes:
                                # Group bets by outcome
                                bets_by_outcome = {outcome: [] for outcome in outcomes}
                                for bet in data[market]:
                                    bets_by_outcome[bet['Team']].append(bet)
                                
                                # Calculate average true probability for each outcome
                                avg_true_probs = {}
                                for outcome, bets in bets_by_outcome.items():
                                    implied_probs = [1 / bet['Odds'] for bet in bets]
                                    avg_implied_prob = sum(implied_probs) / len(implied_probs)
                                    avg_true_probs[outcome] = avg_implied_prob
                                
                                # Normalize probabilities
                                total_prob = sum(avg_true_probs.values())
                                for outcome in avg_true_probs:
                                    avg_true_probs[outcome] /= total_prob
                                
                                # Now evaluate each bet using the average true probabilities
                                for bet in data[market]:
                                    true_prob = avg_true_probs[bet['Team']]
                                    ev = calculate_ev(bet['Odds'], true_prob)
                                    
                                    if MIN_EV_THRESHOLD <= ev <= MAX_EV_THRESHOLD:
                                        positive_ev_bets.append({
                                            'Sport': sport,
                                            'Game': game,
                                            'Team': bet['Team'],
                                            'Bookmaker': bet['Bookmaker'],
                                            'Bet Type': bet['Bet Type'],
                                            'Odds': bet['Odds'],
                                            'EV': ev,
                                            'Start Time': bet['Start Time']
                                        })
                        else:
                            # For non-soccer sports or other markets
                            # Group bets by outcome
                            outcomes = set(bet['Team'] for bet in data[market])
                            bets_by_outcome = {outcome: [] for outcome in outcomes}
                            for bet in data[market]:
                                bets_by_outcome[bet['Team']].append(bet)
                            
                            # Calculate average true probability for each outcome
                            avg_true_probs = {}
                            for outcome, bets in bets_by_outcome.items():
                                implied_probs = [1 / bet['Odds'] for bet in bets]
                                avg_implied_prob = sum(implied_probs) / len(implied_probs)
                                avg_true_probs[outcome] = avg_implied_prob
                            
                            # Normalize probabilities
                            total_prob = sum(avg_true_probs.values())
                            for outcome in avg_true_probs:
                                avg_true_probs[outcome] /= total_prob
                            
                            # Now evaluate each bet using the average true probabilities
                            for bet in data[market]:
                                true_prob = avg_true_probs[bet['Team']]
                                ev = calculate_ev(bet['Odds'], true_prob)
                                print(bet['Team'], ev)
                                if MIN_EV_THRESHOLD <= ev <= MAX_EV_THRESHOLD:
                                    bet_info = {
                                        'Sport': sport,
                                        'Game': game,
                                        'Team': bet['Team'],
                                        'Bookmaker': bet['Bookmaker'],
                                        'Bet Type': bet['Bet Type'],
                                        'Odds': bet['Odds'],
                                        'EV': ev,
                                        'Start Time': bet['Start Time']
                                    }
                                    if market == 'spread':
                                        bet_info['Spread'] = bet['Spread']
                                    positive_ev_bets.append(bet_info)

    return positive_ev_bets, games, arbitrage_opportunities

def format_bet_recommendation(bet):
    american_odds = decimal_to_american(bet['Odds'])
    base_string = (f"{bet['Sport']} - {bet['Game']} (Start: {bet['Start Time']})\n"
                   f"  Bet Type: {bet['Bet Type']}\n"
                   f"  Bookmaker: {bet['Bookmaker']}\n"
                   f"  Odds: {bet['Odds']:.2f} (Decimal) / {american_odds} (American)\n"
                   f"  Expected Value: {bet['EV']:.2%}\n")
    
    if 'Team' in bet:
        base_string += f"  Team/Outcome: {bet['Team']}\n"
    if 'Spread' in bet:
        base_string += f"  Spread: {bet['Spread']}\n"
    if 'Total' in bet:
        base_string += f"  Total: {bet['Total']}\n"
    if 'Stake' in bet:
        base_string += f"  Recommended Stake: {bet['Stake']:.2f}\n"
    
    return base_string

def format_arbitrage_opportunity(opportunity):
    base_string = (f"Market: {opportunity['Market']}\n"
                   f"Date: {opportunity['Date']}\n"
                   f"Profit: {opportunity['Profit']:.2f}%\n"
                   f"Total Investment: {opportunity['Total Investment']:.2f}\n"
                   f"Bets:\n")
    
    for bet in opportunity['Bets']:
        american_odds = decimal_to_american(bet['Odds'])
        base_string += (f"  - Type: {bet['Type']}\n"
                        f"    Bookmaker: {bet['Bookmaker']}\n"
                        f"    Odds: {bet['Odds']:.2f} (Decimal) / {american_odds} (American)\n"
                        f"    Stake: {bet['Stake']:.2f}\n")
        if 'Total' in bet:
            base_string += f"    Total: {bet['Total']}\n"
    
    return base_string

def main(filename):
    positive_ev_bets, games, arbitrage_opportunities = analyze_odds(filename)
    
    os.makedirs('logs', exist_ok=True)
    log_filename = f"logs/betting_recommendations_{datetime.now(EST).strftime('%Y%m%d_%H%M%S')}.txt"
    
    with open(log_filename, 'w') as log_file:
        log_file.write("Betting Recommendations:\n\n")
        
        log_file.write("Configuration:\n")
        log_file.write(f"Allowed Bookmakers: {', '.join(ALLOWED_BOOKMAKERS)}\n")
        log_file.write(f"Max Days Ahead: {MAX_DAYS_AHEAD}\n")
        log_file.write(f"Max Opportunities Per Game: {MAX_OPPORTUNITIES_PER_GAME}\n")
        log_file.write(f"EV Range: {MIN_EV_THRESHOLD:.2%} to {MAX_EV_THRESHOLD:.2%}\n\n")

        log_file.write("Data Summary:\n")
        for sport, sport_games in games.items():
            log_file.write(f"{sport}:\n")
            for game, data in sport_games.items():
                log_file.write(f"  {game}:\n")
                for market in ['moneyline', 'spread', 'total']:
                    if market in data:
                        log_file.write(f"    {market.capitalize()}: {len(data[market])} odds\n")
        log_file.write("\n")

        if positive_ev_bets:
            log_file.write("High Value Bets:\n")
            for bet in sorted(positive_ev_bets, key=lambda x: x['EV'], reverse=True)[:10]:  # Top 10 EV bets
                log_file.write(format_bet_recommendation(bet))
                log_file.write("\n")
        else:
            log_file.write("No high value bets found.\n")

        if arbitrage_opportunities:
            log_file.write("\nArbitrage Opportunities:\n")
            for opportunity in sorted(arbitrage_opportunities, key=lambda x: x['Profit'], reverse=True):
                log_file.write(format_arbitrage_opportunity(opportunity))
                log_file.write("\n")
        else:
            log_file.write("\nNo arbitrage opportunities found.\n")

        # Summary at the bottom
        log_file.write("\nBetting Strategy Summary:\n")
        log_file.write(f"- High Value Bets: {len(positive_ev_bets)}\n")
        log_file.write(f"- Arbitrage Opportunities: {len(arbitrage_opportunities)}\n")

    print(f"Betting recommendations have been saved to {log_filename}")
    
    # Print the summary to the console
    with open(log_filename, 'r') as log_file:
        content = log_file.read()
        print(content)
    
    return log_filename

if __name__ == "__main__":
    import sys
    if len(sys.argv) != 2:
        print("Usage: python script_name.py <path_to_csv_file>")
        sys.exit(1)
    main(sys.argv[1])