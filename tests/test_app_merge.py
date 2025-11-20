from app import merge_ocr_results


def test_merge_prefers_easy_for_dates_and_serial():
    tess = {'vaccine_name': None, 'product_name': None, 'manufacturer': None, 'registration_number': '1F 2/56 (8)', 'serial_number': None, 'mfg_date': None, 'exp_date': None}
    easy = {'vaccine_name': 'Rabies Vaccine', 'product_name': 'DEFENSOR', 'manufacturer': 'Zorts Inc', 'registration_number': 'SCR 643797', 'serial_number': '643797', 'mfg_date': '22 Jan 2023', 'exp_date': '11 Jun 2024'}
    hybrid = {}

    merged = merge_ocr_results(tess, easy, hybrid)
    data = merged['data']
    sources = merged['sources']

    assert data['serial_number'] == '643797'
    assert data['mfg_date'] == '22 Jan 2023'
    assert data['exp_date'] == '11 Jun 2024'
    # registration should prefer tess because it looks like reg
    assert data['registration_number'] == '1F 2/56 (8)'
    assert sources['registration_number']['source'] == 'tesseract'
    assert sources['serial_number']['source'] == 'easyocr'
