from pipeline.geo import haversine_m, point_line_distance_m, to_wkt


def test_haversine_known_distance_dongtan_to_osan():
    d = haversine_m(37.2001, 127.0960, 37.1452, 127.0670)
    assert 5800 < d < 6800


def test_point_line_distance_perpendicular():
    line = [(37.0, 127.0), (37.0, 127.01)]
    assert abs(point_line_distance_m(37.001, 127.005, line) - 111.2) < 2


def test_point_line_distance_beyond_segment_end_uses_endpoint():
    line = [(37.0, 127.0), (37.0, 127.01)]
    expected = haversine_m(37.0, 127.02, 37.0, 127.01)
    assert abs(point_line_distance_m(37.0, 127.02, line) - expected) < 2


def test_point_line_single_point_equals_haversine():
    d = point_line_distance_m(37.2, 127.1, [(37.21, 127.11)])
    assert abs(d - haversine_m(37.2, 127.1, 37.21, 127.11)) < 0.5


def test_wkt_point_lon_first():
    assert to_wkt([(37.1, 127.2)]) == "POINT(127.2 37.1)"


def test_wkt_linestring():
    assert to_wkt([(37.1, 127.2), (37.3, 127.4)]) == "LINESTRING(127.2 37.1, 127.4 37.3)"
