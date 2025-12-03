from flask import Flask, render_template, request, jsonify, send_from_directory
from flask_cors import CORS
import os
import cv2
import time
import json
import numpy as np
from datetime import datetime
from werkzeug.utils import secure_filename

from preprocessing import (
    split_image_left_right,
    preprocess_left_region,
    preprocess_right_region,
    rotate_90
)
from ocr_engines import (
    ocr_hybrid,
    ocr_tesseract_only,
    ocr_easyocr_only
)
from data_extraction import (
    extract_vaccine_data,
    validate_vaccine_data,
    format_output_thai,
    THAI_FIELDS
)
from data_extraction import format_registration_number
import re


VALID_MONTHS = {'JAN', 'FEB', 'MAR', 'APR', 'MAY', 'JUN', 'JUL', 'AUG', 'SEP', 'OCT', 'NOV', 'DEC',
                'Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'}


def score_date_format(date_str):
    if not date_str or date_str == 'ไม่พบ':
        return 0

    parts = date_str.strip().split()
    if len(parts) != 3:
        return 0

    score = 0
    day, month, year = parts

    if day.isdigit() and 1 <= int(day) <= 31:
        score += 33

    if month in VALID_MONTHS:
        score += 34

    if year.isdigit() and 2000 <= int(year) <= 2030:
        score += 33

    return score


def score_registration_number(reg_str):
    if not reg_str or reg_str == 'ไม่พบ':
        return 0

    score = 0

    if '/' in reg_str:
        score += 40

        slash_pattern = re.search(r'\d+/\d+', reg_str)
        if slash_pattern:
            score += 30

    prefix_pattern = re.search(r'([A-Z0-9]{1,3})\s*\d+/\d+', reg_str)
    if prefix_pattern:
        score += 20

    suffix_pattern = re.search(r'\(([A-Z0-9]+)\)', reg_str)
    if suffix_pattern:
        suffix = suffix_pattern.group(1)
        if re.fullmatch(r'[A-Z]{1,2}', suffix):
            score += 10
        elif re.fullmatch(r'[0-9]{1,2}', suffix):
            score += 5

    return min(score, 100)


def score_serial_number(serial_str):
    if not serial_str or serial_str == 'ไม่พบ':
        return 0

    clean = re.sub(r'[^A-Z0-9]', '', serial_str.upper())

    if len(clean) < 5:
        return 0

    score = 0

    if 5 <= len(clean) <= 9:
        score += 50

    digit_part = re.match(r'^(\d+)', clean)
    if digit_part:
        digits = digit_part.group(1)
        if 5 <= len(digits) <= 7:
            score += 30

    letter_part = re.search(r'([A-Z]+)$', clean)
    if letter_part:
        letters = letter_part.group(1)
        if len(letters) <= 2:
            score += 20
    else:
        score += 20

    pattern = re.fullmatch(r'\d{5,7}[A-Z]{0,2}', clean)
    if pattern:
        return 100

    return min(score, 100)


def score_field_value(field_name, value):
    if not value or value == 'ไม่พบ':
        return 0

    if field_name in ['mfg_date', 'exp_date']:
        return score_date_format(value)
    elif field_name == 'registration_number':
        return score_registration_number(value)
    elif field_name == 'serial_number':
        return score_serial_number(value)
    elif field_name in ['vaccine_name', 'product_name']:
        if len(value.strip()) >= 3:
            return 100
        elif len(value.strip()) >= 1:
            return 50
        return 0

    return 100


def calculate_field_level_accuracy(tess_data, easy_data, merged_data):
    field_names = ['vaccine_name', 'product_name', 'registration_number', 'serial_number', 'mfg_date', 'exp_date']
    field_accuracy = {}

    for field in field_names:
        tess_val = tess_data.get(field)
        easy_val = easy_data.get(field)
        merged_val = merged_data.get(field)

        tess_score = score_field_value(field, tess_val)
        easy_score = score_field_value(field, easy_val)
        merged_score = score_field_value(field, merged_val)

        field_accuracy[field] = {
            'tesseract': tess_score,
            'easyocr': easy_score,
            'merged': merged_score,
            'tesseract_value': tess_val or '',
            'easyocr_value': easy_val or '',
            'merged_value': merged_val or ''
        }

    return field_accuracy


def calculate_merge_quality_score(tess_data, easy_data, merged_data):
    field_names = ['vaccine_name', 'product_name', 'registration_number', 'serial_number', 'mfg_date', 'exp_date']

    def calculate_average_score(data):
        total_score = 0
        for field in field_names:
            total_score += score_field_value(field, data.get(field))
        return total_score / len(field_names)

    tess_accuracy = calculate_average_score(tess_data)
    easy_accuracy = calculate_average_score(easy_data)
    merged_accuracy = calculate_average_score(merged_data)

    best_individual = max(tess_accuracy, easy_accuracy)
    improvement = merged_accuracy - best_individual

    return {
        'tesseract_accuracy': round(tess_accuracy, 1),
        'easyocr_accuracy': round(easy_accuracy, 1),
        'merged_accuracy': round(merged_accuracy, 1),
        'best_individual': round(best_individual, 1),
        'improvement': round(improvement, 1),
        'improvement_percentage': round(improvement, 1)
    }


def create_merge_decision_explanation(tess_data, easy_data, merged_data, sources):
    field_names = ['vaccine_name', 'product_name', 'registration_number', 'serial_number', 'mfg_date', 'exp_date']
    decisions = {}

    for field in field_names:
        tess_val = tess_data.get(field, '')
        easy_val = easy_data.get(field, '')
        merged_val = merged_data.get(field, '')
        source_info = sources.get(field, {})

        source = source_info.get('source', 'unknown')
        reason = source_info.get('reason', '')

        match = (tess_val == easy_val) if (tess_val and easy_val) else False

        decisions[field] = {
            'tesseract': tess_val or 'ไม่พบ',
            'easyocr': easy_val or 'ไม่พบ',
            'selected': merged_val or 'ไม่พบ',
            'source': source,
            'reason': reason,
            'engines_agree': match
        }

    return decisions


def merge_ocr_results(tess_data: dict, easy_data: dict, hybrid_data: dict) -> dict:
    def choose_field(key):
        e = easy_data.get(key)
        h = hybrid_data.get(key)
        t = tess_data.get(key)
        if key == 'registration_number':
            e_form = format_registration_number(e) if e else None
            t_form = format_registration_number(t) if t else None
            h_form = format_registration_number(h) if h else None
            if e_form:
                return e_form, 'easyocr', 'preferred-canonical'
            if t_form:
                return t_form, 'tesseract', 'preferred-canonical'
            if h_form:
                return h_form, 'hybrid', 'preferred-canonical'
            return None, 'none', 'no-canonical-found'
        else:
            if key == 'vaccine_name':
                def split_components(s):
                    if not s:
                        return []
                    parts = re.split(r'[;\n,]+', s)
                    return [p.strip() for p in parts if p.strip()]

                t_comps = split_components(t)
                e_comps = split_components(e)
                h_comps = split_components(h)

                merged_list = []
                seen = set()
                for comp in (t_comps + e_comps + h_comps):
                    low = comp.lower()
                    if low not in seen:
                        merged_list.append(comp)
                        seen.add(low)

                merged_name = '; '.join(merged_list) if merged_list else (e or h or t)

                src = 'none'
                reason = 'missing'
                if t and ('FELINE' in (t or '').upper() or len(t_comps) > len(e_comps)):
                    src = 'tesseract'
                    reason = 'preferred-by-content'
                elif e:
                    src = 'easyocr'
                    reason = 'easy-present'
                elif h:
                    src = 'hybrid'
                    reason = 'hybrid-present'

                return merged_name, src, reason
            if e:
                return e, 'easyocr', 'easy-present'
            if h:
                return h, 'hybrid', 'hybrid-present'
            if t:
                return t, 'tesseract', 'tesseract-present'
            return None, 'none', 'missing'

    merged_fields = {}
    merged_sources = {}
    for k in ['vaccine_name', 'product_name', 'manufacturer', 'registration_number', 'serial_number', 'mfg_date', 'exp_date']:
        val, src, reason = choose_field(k)
        merged_fields[k] = val
        merged_sources[k] = {'source': src, 'reason': reason}

    return {
        'data': merged_fields,
        'sources': merged_sources,
        'formatted_output': format_output_thai(merged_fields)
    }

app = Flask(__name__)
CORS(app, resources={
    r"/api/*": {
        "origins": "*",
        "methods": ["GET", "POST", "OPTIONS"],
        "allow_headers": ["Content-Type"],
        "supports_credentials": False
    }
})

# กำหนดค่า
UPLOAD_FOLDER = os.path.join(os.path.dirname(__file__), 'uploads')
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg'}
MAX_FILE_SIZE = 5 * 1024 * 1024 

os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = MAX_FILE_SIZE

@app.errorhandler(500)
def internal_error(error):
    return jsonify({'error': 'Internal server error', 'details': str(error)}), 500

@app.errorhandler(404)
def not_found(error):
    return jsonify({'error': 'Not found'}), 404

@app.route('/uploads/<path:filename>')
def uploaded_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)


def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


def save_image(image: np.ndarray, filepath: str) -> bool:
    try:
        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        
        # ตรวจสอบให้แน่ใจว่าเป็น dtype uint8
        if image.dtype != np.uint8:
            image = cv2.normalize(image, None, 0, 255, cv2.NORM_MINMAX)
            image = image.astype(np.uint8)
        
        return cv2.imwrite(filepath, image)
    except Exception as e:
        print(f'เกิดข้อผิดพลาดในการบันทึก {filepath}: {e}')
        return False


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/test')
def test_preprocessing():
    return render_template('test_preprocessing.html')


@app.route('/api/test_preprocessing', methods=['POST'])
def api_test_preprocessing():
    try:
        if 'file' not in request.files:
            return jsonify({'error': 'No file provided'}), 400
        
        file = request.files['file']
        if file.filename == '':
            return jsonify({'error': 'No file selected'}), 400
        
        # ดึงพารามิเตอร์แบบที่เรากำหนดเอง
        params = json.loads(request.form.get('params', '{}'))
        scale = params.get('scale', 7)
        alpha = params.get('alpha', 1.3)
        beta = params.get('beta', 4)
        block_size = params.get('block_size', 25)
        c_value = params.get('c_value', 2)
        
        # บันทึกไฟล์ที่อัปโหลด
        filename = secure_filename(file.filename)
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"{timestamp}_{filename}"
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(filepath)
        
        # โหลดรูปภาพ
        image = cv2.imread(filepath)
        if image is None:
            return jsonify({'error': 'Failed to load image'}), 400
        
        # แบ่ง
        left, right = split_image_left_right(image)
        
        # การประมวลผลล่วงหน้าที่เรากำหนดบริเวณด้านขวา
        start_time = time.time()
        
        height, width = right.shape[:2]
        scaled = cv2.resize(right, (width*scale, height*scale), 
                           interpolation=cv2.INTER_CUBIC)
        
        rotated = rotate_90(scaled)
        
        gray = cv2.cvtColor(rotated, cv2.COLOR_BGR2GRAY) if len(rotated.shape) == 3 else rotated
        inverted = cv2.bitwise_not(gray)
        
        bilateral = cv2.bilateralFilter(inverted, 9, 75, 75)
        
        clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8, 8))
        clahe_applied = clahe.apply(bilateral)
        
        # ใช้พารามิเตอร์ที่กำหนดเอง
        enhanced = cv2.convertScaleAbs(clahe_applied, alpha=alpha, beta=beta)
        binary = cv2.adaptiveThreshold(
            enhanced, 255,
            cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
            cv2.THRESH_BINARY,
            blockSize=block_size, C=c_value
        )
        
        white_percent = (binary == 255).sum() / binary.size * 100
        processing_time = time.time() - start_time
        
        # บันทึกรูปภาพทดสอบ
        temp_dir = os.path.join(app.config['UPLOAD_FOLDER'], 'test')
        os.makedirs(temp_dir, exist_ok=True)
        
        original_path = os.path.join(temp_dir, f'{timestamp}_original.png')
        right_raw_path = os.path.join(temp_dir, f'{timestamp}_right_raw.png')
        right_processed_path = os.path.join(temp_dir, f'{timestamp}_right_processed.png')
        
        save_image(image, original_path)
        save_image(right, right_raw_path)
        save_image(binary, right_processed_path)
        
        return jsonify({
            'success': True,
            'white_percent': round(white_percent, 1),
            'method': f'Adaptive (alpha={alpha}, beta={beta}, block={block_size}, C={c_value})',
            'image_size': [binary.shape[0], binary.shape[1]],
            'processing_time': round(processing_time, 3),
            'images': {
                'original': f'/uploads/test/{timestamp}_original.png',
                'right_raw': f'/uploads/test/{timestamp}_right_raw.png',
                'right_processed': f'/uploads/test/{timestamp}_right_processed.png'
            }
        })

    except Exception as e:
        print(f'ข้อผิดพลาดใน test_preprocessing: {e}')
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500


@app.route('/api/process', methods=['POST', 'OPTIONS'])
def process_image():
    if request.method == 'OPTIONS':
        response = jsonify({'status': 'ok'})
        response.headers.add('Access-Control-Allow-Origin', '*')
        response.headers.add('Access-Control-Allow-Headers', 'Content-Type')
        response.headers.add('Access-Control-Allow-Methods', 'POST, OPTIONS')
        return response, 200

    try:
        # ตรวจสอบไฟล์
        if 'file' not in request.files:
            return jsonify({'error': 'No file provided'}), 400
        
        file = request.files['file']
        
        if file.filename == '':
            return jsonify({'error': 'No file selected'}), 400
        
        if not allowed_file(file.filename):
            return jsonify({'error': 'Only JPG, PNG files allowed'}), 400
        
        # บันทึกไฟล์
        filename = secure_filename(file.filename)
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"{timestamp}_{filename}"
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(filepath)
        
        print(f'\n{"="*60}')
        print(f'Processing: {filename}')
        print(f'{"="*60}')

        # โหลดรูปภาพ
        image = cv2.imread(filepath)
        if image is None:
            return jsonify({'error': 'ไม่สามารถโหลดรูปภาพได้'}), 400

        # แบ่งรูปภาพ
        print('กำลังแบ่งรูปภาพ...')
        left, right = split_image_left_right(image)
        
        # สร้างไดเรกทอรีชั่วคราว
        temp_dir = os.path.join(app.config['UPLOAD_FOLDER'], 'temp')
        os.makedirs(temp_dir, exist_ok=True)
        
        # ประมวลผล
        print('กำลังประมวลผล...')
        left_processed = preprocess_left_region(left, scale=2)
        right_processed = preprocess_right_region(right, scale=7)
        
        # บันทึกรูปภาพที่ประมวลผลแล้ว
        left_path = os.path.join(temp_dir, f'{timestamp}_left.png')
        right_path = os.path.join(temp_dir, f'{timestamp}_right.png')
        save_image(left_processed, left_path)
        save_image(right_processed, right_path)
        
        # TESSERACT
        print('\nกำลังประมวลผลด้วย Tesseract...')
        start_time = time.time()

        # ใช้ Tesseract สำหรับทั้งสองข้าง
        tess_results = ocr_tesseract_only(left_processed, right_processed)
        tess_data = extract_vaccine_data(
            tess_results['left_text'],
            tess_results['right_text']
        )
        tess_validation = validate_vaccine_data(tess_data)

        tess_time = time.time() - start_time
        print(f'Time: {tess_time:.2f}s')
        print(f'Complete: {tess_validation["is_complete"]}')

        # EASYOCR
        print('\nกำลังประมวลผลด้วย EasyOCR...')
        start_time = time.time()

        # ใช้ EasyOCR สำหรับทั้งสองข้าง
        easy_results = ocr_easyocr_only(left_processed, right_processed)
        easy_data = extract_vaccine_data(
            easy_results['left_text'],
            easy_results['right_text']
        )
        easy_validation = validate_vaccine_data(easy_data)

        easy_time = time.time() - start_time
        print(f'Time: {easy_time:.2f}s')
        print(f'Complete: {easy_validation["is_complete"]}')

        # นำมารวมกัน
        print('\n กำลังประมวลผลด้วยการนำมารวมกัน...')
        start_time = time.time()

        # ใช้ Tesseract สำหรับด้านซ้าย, EasyOCR สำหรับด้านขวา
        hybrid_results = ocr_hybrid(left_processed, right_processed)
        hybrid_data = extract_vaccine_data(
            hybrid_results['left_text'],
            hybrid_results['right_text']
        )
        hybrid_validation = validate_vaccine_data(hybrid_data)

        hybrid_time = time.time() - start_time
        print(f'Time: {hybrid_time:.2f}s')
        print(f'Complete: {hybrid_validation["is_complete"]}')
        
        # คำนวณเมตริก
        def count_detected(data):
            return sum(1 for v in data.values() if v and v != 'ไม่พบ')
        
        tess_detected = count_detected(tess_data)
        easy_detected = count_detected(easy_data)
        hybrid_detected = count_detected(hybrid_data)
        
        total_fields = len(THAI_FIELDS)
        
        metrics = {
            'tesseract': {
                'fields_detected': tess_detected,
                'total_fields': total_fields,
                'accuracy': round((tess_detected / total_fields) * 100, 1),
                'processing_time': round(tess_time, 2),
                'is_complete': tess_validation['is_complete']
            },
            'easyocr': {
                'fields_detected': easy_detected,
                'total_fields': total_fields,
                'accuracy': round((easy_detected / total_fields) * 100, 1),
                'processing_time': round(easy_time, 2),
                'is_complete': easy_validation['is_complete']
            },
            'hybrid': {
                'fields_detected': hybrid_detected,
                'total_fields': total_fields,
                'accuracy': round((hybrid_detected / total_fields) * 100, 1),
                'processing_time': round(hybrid_time, 2),
                'is_complete': hybrid_validation['is_complete']
            }
        }
        
        # กำหนดว่าอะไรดีที่สุด
        if hybrid_detected >= max(tess_detected, easy_detected):
            winner = 'Hybrid'
        elif easy_detected > tess_detected:
            winner = 'EasyOCR'
        else:
            winner = 'Tesseract'
        
        metrics['comparison'] = {
            'winner': winner,
            'recommendation': 'Hybrid (Tesseract + EasyOCR)' if winner == 'Hybrid' else f'{winner}'
        }
        
        # พิมพ์สรุปผลลัพธ์
        print(f'\n{"="*60}')
        print('RESULTS SUMMARY')
        print(f'{"="*60}')
        print(f'Tesseract:  {tess_detected}/{total_fields} fields ({metrics["tesseract"]["accuracy"]}%)')
        print(f'EasyOCR:    {easy_detected}/{total_fields} fields ({metrics["easyocr"]["accuracy"]}%)')
        print(f'Hybrid:     {hybrid_detected}/{total_fields} fields ({metrics["hybrid"]["accuracy"]}%)')
        print(f'Winner:     {winner}')
        print(f'{"="*60}\n')
        
        # เตรียมการตอบกลับ
        response = {
            'success': True,
            'filename': filename,
            'images': {
                'original': f'/uploads/{filename}',
                'left_preprocessed': f'/uploads/temp/{timestamp}_left.png',
                'right_preprocessed': f'/uploads/temp/{timestamp}_right.png'
            },
            'tesseract': {
                'data': tess_data,
                'validation': tess_validation,
                'formatted_output': format_output_thai(tess_data),
                'raw_left': tess_results.get('left_text', ''),
                'raw_right': tess_results.get('right_text', '')
            },
            'easyocr': {
                'data': easy_data,
                'validation': easy_validation,
                'formatted_output': format_output_thai(easy_data),
                'raw_left': easy_results.get('left_text', ''),
                'raw_right': easy_results.get('right_text', '')
            },
            'hybrid': {
                'data': hybrid_data,
                'validation': hybrid_validation,
                'formatted_output': format_output_thai(hybrid_data),
                'raw_left': hybrid_results.get('left_text', ''),
                'raw_right': hybrid_results.get('right_text', '')
            },
            'merged': merge_ocr_results(tess_data, easy_data, hybrid_data),
            'metrics': metrics
        }

        merged_result = response['merged']
        merged_data = merged_result['data']
        merged_sources = merged_result['sources']

        field_level_accuracy = calculate_field_level_accuracy(tess_data, easy_data, merged_data)
        merge_quality = calculate_merge_quality_score(tess_data, easy_data, merged_data)
        merge_decisions = create_merge_decision_explanation(tess_data, easy_data, merged_data, merged_sources)

        response['metrics']['field_level_accuracy'] = field_level_accuracy
        response['metrics']['merge_quality'] = merge_quality
        response['metrics']['merge_decisions'] = merge_decisions

        print('ประมวลผลเสร็จสมบูรณ์!\n')

        return jsonify(response)

    except Exception as e:
        print(f'\nข้อผิดพลาดใน process_image: {e}')
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500


@app.route('/api/health', methods=['GET'])
def health_check():
    return jsonify({
        'status': 'healthy',
        'timestamp': datetime.now().isoformat(),
        'upload_folder': app.config['UPLOAD_FOLDER'],
        'max_file_size': app.config['MAX_CONTENT_LENGTH']
    })


if __name__ == '__main__':
    print('='*60)
    print('เว็บ OCR สำหรับวัคซีน - พร้อมใช้งาน')
    print('='*60)
    print(f'Upload folder: {UPLOAD_FOLDER}')
    print(f'Max file size: {MAX_FILE_SIZE / 1024 / 1024:.1f} MB')
    print(f'Server: http://localhost:5001')
    print('='*60)
    print()

    app.run(debug=True, host='0.0.0.0', port=5001)