# run_ev_analysis.py

import os
from analysis.ev_analysis import main as analyze_odds

def list_csv_files():
    csv_files = [f for f in os.listdir('data') if f.endswith('.csv')]
    return csv_files

def main():
    csv_files = list_csv_files()
    
    if not csv_files:
        print("No CSV files found in the 'data' folder.")
        return

    print("Available CSV files:")
    for i, file in enumerate(csv_files, 1):
        print(f"{i}. {file}")

    while True:
        try:
            choice = int(input("\nEnter the number of the CSV file you want to analyze: "))
            if 1 <= choice <= len(csv_files):
                selected_file = csv_files[choice - 1]
                break
            else:
                print("Invalid choice. Please enter a number from the list.")
        except ValueError:
            print("Invalid input. Please enter a number.")

    csv_file_path = os.path.join('data', selected_file)
    print(f"\nAnalyzing odds data from {csv_file_path}...")
    log_file = analyze_odds(csv_file_path)
    
    print(f"\nAnalysis complete. Detailed recommendations have been saved to {log_file}")
    print("\nBetting Recommendations Summary:")
    
    with open(log_file, 'r') as f:
        content = f.read()
        print(content)

if __name__ == "__main__":
    main()