from data_extraction import extract_vaccine_data


def test_extract_sample():
    # Simulated OCR outputs (left and right) mimicking noisy OCR
    left_text = (
        "DOSE IMI FOR ANIMAL TREATMENT ONLY RABIES VACCINE KILLED VIRUS ZOETIS "
        "DEFENSOR 3"
    )
    right_text = (
        "SER 643797 MFG: 22 JAN 23 EXP 11 JUN 24 REG NO 1F 2/56 (B)"
    )

    data = extract_vaccine_data(left_text, right_text)

    assert data.get('product_name') is not None
    assert 'DEFENSOR' in data.get('product_name')
    assert data.get('serial_number') == '643797'
    assert data.get('mfg_date') == '22 Jan 2023'
    assert data.get('exp_date') == '11 Jun 2024'
    assert data.get('registration_number') is not None


def test_feline_extraction():
    tess_left = "Feline Rhinotracheitis; Calici-Panleukopenia; Chlamydia psittaci\nReg No NO 190"
    tess_right = ""

    easy_left = "Calici-Panleukopenia; Chlamydia psittaci\nReg No 2F18/59 (B) SER"
    easy_right = "Ser 739176C\nMFG 26 EXP 2005\nEXP 05 ROV 2025"

    tess_data = extract_vaccine_data(tess_left, tess_right)
    easy_data = extract_vaccine_data(easy_left, easy_right)

    # reuse merge logic from app
    from app import merge_ocr_results
    merged = merge_ocr_results(tess_data, easy_data, easy_data)

    assert merged['data']['registration_number'] == '2F18/59 (B)'
    assert merged['data']['serial_number'] == '739176C'
    assert merged['data']['exp_date'] == '05 Nov 2025'
