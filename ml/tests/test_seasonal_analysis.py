from src.seasonal_analysis import aggregate_seasons

def test_seasonal_aggregation():
    result = aggregate_seasons([{"month":4,"interval_volume_litres":10},{"month":8,"interval_volume_litres":5}])
    by_name = {r["season"]:r for r in result}
    assert by_name["Summer"]["total_litres"] == 10
    assert by_name["Monsoon"]["total_litres"] == 5
