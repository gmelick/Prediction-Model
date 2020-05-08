from Import_Batter_Stats import get_batter_stats
from Batter_Similarities import compute_batter_similarities
from PitchFX import load_pitch_fx_day_data, refresh_pitch_fx_data
from Pitcher_Similarities import compute_pitcher_similarities
from Online_to_Excel import refresh_season, process_day
from Bootstrap import simulate_day
from datetime import date, datetime, timedelta
import time

cur_date = datetime.now()
live = False
# refresh_pitch_fx_data(cur_date)
# refresh_season(cur_date)
while True:
    cmp_date = datetime.now()
    if cur_date.day == cmp_date.day and cmp_date.hour > 7 and live:
        print("Importing Batter Statistics")
        get_batter_stats(cur_date)
        print("Calculating Batter Similarities")
        compute_batter_similarities(cur_date.year)
        print("Loading PitchFX data")
        load_pitch_fx_day_data(cur_date)
        print("Computing Pitcher Similarities")
        compute_pitcher_similarities(cur_date.year)
        print("Loading Online Data")
        process_day(cur_date)
        print(f"Simulating Day: {cur_date}")
        simulate_day(cur_date)
        print("Refreshing PitchFX data")
        refresh_pitch_fx_data(cur_date)
        print("Refreshing Online Data")
        refresh_season(cur_date)
        cur_date += timedelta(1)
    elif not live:
        start_date = date(2019, 3, 28)
        end_date = date(2020, 1, 1)
        while start_date < end_date:
            print("Importing Batter Statistics")
            get_batter_stats(start_date)
            print("Calculating Batter Similarities")
            compute_batter_similarities(start_date.year)
            print("Loading PitchFX data")
            load_pitch_fx_day_data(start_date)
            print("Computing Pitcher Similarities")
            compute_pitcher_similarities(start_date.year)
            print("Loading Online Data")
            process_day(start_date)
            print(f"Simulating Day: {start_date}")
            simulate_day(start_date)
            print("Refreshing PitchFX data")
            refresh_pitch_fx_data(start_date)
            print("Refreshing Online Data")
            refresh_season(start_date)
            start_date += timedelta(1)
    else:
        time.sleep(3600)
