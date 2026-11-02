from pipeline.fetch_public import decode_csv, date_from_title


def test_decode_csv_handles_utf8_bom_and_cp949():
    text = "번호,쉼터명\n1,동탄1동 경로당\n"
    for raw in (("\ufeff" + text).encode("utf-8"), text.encode("cp949")):
        assert decode_csv(raw) == [{"번호": "1", "쉼터명": "동탄1동 경로당"}]


def test_decode_csv_strips_header_spaces():
    assert decode_csv(" 이름 , 위도 \nA,37.2\n".encode("utf-8")) == [{"이름": "A", "위도": "37.2"}]


def test_date_from_title():
    assert date_from_title("경기도 화성시_무더위쉼터_20261016") == "2026-10-16"
    assert date_from_title("이름만 있는 데이터") == ""
