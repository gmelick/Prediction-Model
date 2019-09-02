import Import_Batter_Stats
import Batter_Similarities
import PitchFX
import Pitcher_Similarities
import Online_to_Excel
import Bootstrap
from datetime import datetime, timedelta
import time

cur_date = datetime.now()
while True:
    cmp_date = datetime.now()
    if cur_date.day == cmp_date.day and cmp_date.hour > 7:
        Import_Batter_Stats.main()
        Batter_Similarities.main()
        PitchFX.main()
        Pitcher_Similarities.main()
        Online_to_Excel.main()
        Bootstrap.main()
        PitchFX.main_alt()
        Online_to_Excel.main_alt()
        cur_date += timedelta(1)
    else:
        time.sleep(3600)
