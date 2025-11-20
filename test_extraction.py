"""
Test Data Extraction
ทดสอบการ extract ข้อมูลจาก OCR text
"""

from data_extraction import (
    extract_vaccine_data,
    validate_vaccine_data,
    format_output_thai
)

# ข้อมูล OCR จากการทดสอบจริง

# Left Region (Tesseract)
left_text = """
dose imi
FOR ANIMAL TREATMENT ONLY
Rabies Vaccine
Killed Virus zoetis
For use in dogs, cats,
and ferrets only
For Veterinary Use Only
Reg No 1F 2/56 (B)
Zoetis Inc.
DEFENSOR 3
"""

# Right Region (EasyOCR) - ข้อความที่มีปัญหา
right_text = """
Ser 64379 22 JN 23 1 Juv 2 8 4to Exp" unlyn?
"""

# Note: จริงๆ ควรเป็น
# Ser 643797 MFG 22 JAN 23 Exp 11 JUN 24

print('='*70)
print('🧪 TESTING DATA EXTRACTION')
print('='*70)

print('\n📄 Input Text:')
print('\nLeft (Tesseract):')
print(left_text.strip())
print('\nRight (EasyOCR - มีปัญหา):')
print(right_text.strip())

# Extract data
data = extract_vaccine_data(left_text, right_text)

print('\n' + '='*70)
print('📊 EXTRACTED DATA')
print('='*70)
print()

# Display in Thai
print(format_output_thai(data))

# Validation
print('\n' + '='*70)
print('✅ VALIDATION')
print('='*70)

validation = validate_vaccine_data(data)
for key, status in validation.items():
    icon = '✅' if status else '❌'
    print(f'{icon} {key}: {status}')

# Summary
print('\n' + '='*70)
if validation['is_complete']:
    print('🎉 ข้อมูลครบถ้วน!')
else:
    print('⚠️ ข้อมูลไม่ครบ - ต้องตรวจสอบ')
print('='*70)

# Show what's missing
if not validation['is_complete']:
    print('\nข้อมูลที่ขาดหาย:')
    if not validation['has_vaccine_name']:
        print('  ❌ ชื่อวัคซีน')
    if not validation['has_serial']:
        print('  ❌ Serial Number')
    if not validation['has_dates']:
        print('  ❌ วันผลิต/วันหมดอายุ')
    if not validation['has_manufacturer']:
        print('  ⚠️ ผู้ผลิต (Optional)')

# Test with better right text
print('\n\n' + '='*70)
print('🔧 TESTING WITH CORRECTED RIGHT TEXT')
print('='*70)

right_text_corrected = """
Ser 643797
MFG 22 JAN 23
Exp 11 JUN 24
"""

print('\nRight (Corrected):')
print(right_text_corrected.strip())

data2 = extract_vaccine_data(left_text, right_text_corrected)
print('\n📊 Extracted:')
print(format_output_thai(data2))

validation2 = validate_vaccine_data(data2)
print('\n✅ Validation:')
for key, status in validation2.items():
    icon = '✅' if status else '❌'
    print(f'{icon} {key}: {status}')

if validation2['is_complete']:
    print('\n🎉 ข้อมูลครบถ้วน!')

# Test different vaccine brands
print('\n\n' + '='*70)
print('🧪 TESTING DIFFERENT VACCINE BRANDS')
print('='*70)

test_cases = [
    {
        'name': 'Nobivac Rabies',
        'left': 'NOBIVAC RABIES\nBoehringer Ingelheim\nReg No 1F 3/57 (B)',
        'right': 'Ser 123456\nMFG 15 MAR 24\nExp 15 MAR 27'
    },
    {
        'name': 'Felocell 4',
        'left': 'FELOCELL 4\nZoetis Inc.\nReg No 2F 1/58 (B)',
        'right': 'Ser 789012\nMFG 01 APR 24\nExp 01 APR 26'
    },
    {
        'name': 'Defensor 3',
        'left': 'DEFENSOR 3\nZoetis Inc.\nReg No 1F 2/56 (B)',
        'right': 'Ser 345678\nMFG 10 FEB 24\nExp 10 FEB 27'
    }
]

for i, test in enumerate(test_cases, 1):
    print(f'\n--- Test Case {i}: {test["name"]} ---')
    result = extract_vaccine_data(test['left'], test['right'])
    val = validate_vaccine_data(result)
    
    print(f'ชื่อวัคซีน: {result.get("vaccine_name") or result.get("product_name") or "ไม่พบ"}')
    print(f'ผู้ผลิต: {result.get("manufacturer") or "ไม่พบ"}')
    print(f'Serial: {result.get("serial_number") or "ไม่พบ"}')
    print(f'วันผลิต: {result.get("mfg_date") or "ไม่พบ"}')
    print(f'วันหมดอายุ: {result.get("exp_date") or "ไม่พบ"}')
    print(f'Status: {"✅ Complete" if val["is_complete"] else "❌ Incomplete"}')

print('\n' + '='*70)
print('🏁 TESTING COMPLETE')
print('='*70)