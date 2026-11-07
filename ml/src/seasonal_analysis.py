def season_for_month(month: int) -> str:
    if month in (3,4,5,6): return "Summer"
    if month in (7,8,9,10): return "Monsoon"
    return "Winter"

def aggregate_seasons(rows):
    totals = {"Summer":0.0,"Monsoon":0.0,"Winter":0.0}
    counts = {key:0 for key in totals}
    for row in rows:
        season = season_for_month(row["month"])
        litres = float(row["interval_volume_litres"])
        if litres < 0: continue
        totals[season] += litres; counts[season] += 1
    return [{"season":s,"total_litres":round(totals[s],2),"reading_count":counts[s],"data_available":counts[s]>0} for s in totals]
