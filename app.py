"""
Vaccine OCR Web Application - Production Ready
Flask backend with Tesseract vs EasyOCR comparison
✅ Updated to match module structure
"""

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
    preprocess_right_region_for_tesseract,
    rotate_90
)
from ocr_engines import (
    ocr_tesseract,
    ocr_easyocr,
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


def merge_ocr_results(tess_data: dict, easy_data: dict, hybrid_data: dict) -> dict:
    """
    Merge OCR outputs into a single preferred result with source metadata.

    Rules:
    - For registration_number prefer Tesseract if it contains '/' or 'REG', else EasyOCR, else Hybrid
    - For product_name, serial_number, mfg_date, exp_date prefer EasyOCR, then Hybrid, then Tesseract
    - Provide source and reason metadata for each field
    """
    def choose_field(key):
        e = easy_data.get(key)
        h = hybrid_data.get(key)
        t = tess_data.get(key)
        if key == 'registration_number':
            # Enforce strict canonical registration: PREFIX N1/N2 (prefix 1-3 alnum, N1/N2 1-3 digits)
            # Use formatted canonical values only; if none match, return missing
            e_form = format_registration_number(e) if e else None
            t_form = format_registration_number(t) if t else None
            h_form = format_registration_number(h) if h else None
            if e_form:
                return e_form, 'easyocr', 'preferred-canonical'
            if t_form:
                return t_form, 'tesseract', 'preferred-canonical'
            if h_form:
                return h_form, 'hybrid', 'preferred-canonical'
            # No canonical registration found — do not return non-canonical values
            return None, 'none', 'no-canonical-found'
        else:
            if key == 'vaccine_name':
                # Merge vaccine name components to avoid losing prefixes like 'Feline'
                def split_components(s):
                    if not s:
                        return []
                    parts = re.split(r'[;\n,]+', s)
                    return [p.strip() for p in parts if p.strip()]

                t_comps = split_components(t)
                e_comps = split_components(e)
                h_comps = split_components(h)

                # Build ordered unique list preferring Tesseract components first
                merged_list = []
                seen = set()
                for comp in (t_comps + e_comps + h_comps):
                    low = comp.lower()
                    if low not in seen:
                        merged_list.append(comp)
                        seen.add(low)

                merged_name = '; '.join(merged_list) if merged_list else (e or h or t)

                # Decide source: prefer tesseract when it contains 'FELINE' or has more components
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
CORS(app)

# Configuration
UPLOAD_FOLDER = os.path.join(os.path.dirname(__file__), 'uploads')
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg'}
MAX_FILE_SIZE = 5 * 1024 * 1024  # 5MB

os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = MAX_FILE_SIZE


@app.route('/uploads/<path:filename>')
def uploaded_file(filename):
    """Serve uploaded files"""
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)


def allowed_file(filename):
    """Check if file extension is allowed"""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


def save_image(image: np.ndarray, filepath: str) -> bool:
    """
    Save image with proper dtype conversion
    
    Args:
        image: Image array
        filepath: Destination path
    
    Returns:
        True if successful
    """
    try:
        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        
        # Ensure uint8 dtype
        if image.dtype != np.uint8:
            image = cv2.normalize(image, None, 0, 255, cv2.NORM_MINMAX)
            image = image.astype(np.uint8)
        
        return cv2.imwrite(filepath, image)
    except Exception as e:
        print(f'❌ Error saving {filepath}: {e}')
        return False


@app.route('/')
def index():
    """Main page"""
    return render_template('index.html')


@app.route('/test')
def test_preprocessing():
    """Test preprocessing page"""
    return render_template('test_preprocessing.html')


@app.route('/api/test_preprocessing', methods=['POST'])
def api_test_preprocessing():
    """
    Test preprocessing with custom parameters
    Used for fine-tuning preprocessing settings
    """
    try:
        if 'file' not in request.files:
            return jsonify({'error': 'No file provided'}), 400
        
        file = request.files['file']
        if file.filename == '':
            return jsonify({'error': 'No file selected'}), 400
        
        # Get custom parameters
        params = json.loads(request.form.get('params', '{}'))
        scale = params.get('scale', 7)
        alpha = params.get('alpha', 1.3)
        beta = params.get('beta', 4)
        block_size = params.get('block_size', 25)
        c_value = params.get('c_value', 2)
        
        # Save uploaded file
        filename = secure_filename(file.filename)
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"{timestamp}_{filename}"
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(filepath)
        
        # Load image
        image = cv2.imread(filepath)
        if image is None:
            return jsonify({'error': 'Failed to load image'}), 400
        
        # Split
        left, right = split_image_left_right(image)
        
        # Custom preprocessing for right region
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
        
        # Apply custom parameters
        enhanced = cv2.convertScaleAbs(clahe_applied, alpha=alpha, beta=beta)
        binary = cv2.adaptiveThreshold(
            enhanced, 255,
            cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
            cv2.THRESH_BINARY,
            blockSize=block_size, C=c_value
        )
        
        white_percent = (binary == 255).sum() / binary.size * 100
        processing_time = time.time() - start_time
        
        # Save test images
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
            'method': f'Adaptive (α={alpha}, β={beta}, block={block_size}, C={c_value})',
            'image_size': [binary.shape[0], binary.shape[1]],
            'processing_time': round(processing_time, 3),
            'images': {
                'original': f'/uploads/test/{timestamp}_original.png',
                'right_raw': f'/uploads/test/{timestamp}_right_raw.png',
                'right_processed': f'/uploads/test/{timestamp}_right_processed.png'
            }
        })
        
    except Exception as e:
        print(f'❌ Error in test_preprocessing: {e}')
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500


@app.route('/api/process', methods=['POST'])
def process_image():
    """
    🎯 MAIN API: Process vaccine image with OCR
    
    Compares Tesseract vs EasyOCR performance
    """
    try:
        # Validate file
        if 'file' not in request.files:
            return jsonify({'error': 'No file provided'}), 400
        
        file = request.files['file']
        
        if file.filename == '':
            return jsonify({'error': 'No file selected'}), 400
        
        if not allowed_file(file.filename):
            return jsonify({'error': 'Only JPG, PNG files allowed'}), 400
        
        # Save file
        filename = secure_filename(file.filename)
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"{timestamp}_{filename}"
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(filepath)
        
        print(f'\n{"="*60}')
        print(f'📂 Processing: {filename}')
        print(f'{"="*60}')
        
        # Load image
        image = cv2.imread(filepath)
        if image is None:
            return jsonify({'error': 'Failed to load image'}), 400
        
        # Split image
        print('✂️  Splitting image...')
        left, right = split_image_left_right(image)
        
        # Create temp directory
        temp_dir = os.path.join(app.config['UPLOAD_FOLDER'], 'temp')
        os.makedirs(temp_dir, exist_ok=True)
        
        # Preprocess
        print('🔧 Preprocessing regions...')
        left_processed = preprocess_left_region(left, scale=2)
        right_processed = preprocess_right_region(right, scale=7)
        
        # Save preprocessed images
        left_path = os.path.join(temp_dir, f'{timestamp}_left.png')
        right_path = os.path.join(temp_dir, f'{timestamp}_right.png')
        save_image(left_processed, left_path)
        save_image(right_processed, right_path)
        
        # === TESSERACT ===
        print('\n🔷 Processing with Tesseract...')
        start_time = time.time()
        
        # Use Tesseract for both regions
        tess_results = ocr_tesseract_only(left_processed, right_processed)
        tess_data = extract_vaccine_data(
            tess_results['left_text'], 
            tess_results['right_text']
        )
        tess_validation = validate_vaccine_data(tess_data)
        
        tess_time = time.time() - start_time
        print(f'   ⏱️  Time: {tess_time:.2f}s')
        print(f'   📊 Complete: {tess_validation["is_complete"]}')
        
        # === EASYOCR ===
        print('\n🔶 Processing with EasyOCR...')
        start_time = time.time()
        
        # Use EasyOCR for both regions
        easy_results = ocr_easyocr_only(left_processed, right_processed)
        easy_data = extract_vaccine_data(
            easy_results['left_text'], 
            easy_results['right_text']
        )
        easy_validation = validate_vaccine_data(easy_data)
        
        easy_time = time.time() - start_time
        print(f'   ⏱️  Time: {easy_time:.2f}s')
        print(f'   📊 Complete: {easy_validation["is_complete"]}')
        
        # === HYBRID (Recommended) ===
        print('\n🏆 Processing with Hybrid Strategy...')
        start_time = time.time()
        
        # Use Tesseract for left, EasyOCR for right
        hybrid_results = ocr_hybrid(left_processed, right_processed)
        hybrid_data = extract_vaccine_data(
            hybrid_results['left_text'], 
            hybrid_results['right_text']
        )
        hybrid_validation = validate_vaccine_data(hybrid_data)
        
        hybrid_time = time.time() - start_time
        print(f'   ⏱️  Time: {hybrid_time:.2f}s')
        print(f'   📊 Complete: {hybrid_validation["is_complete"]}')
        
        # Calculate metrics
        def count_detected(data):
            """Count successfully detected fields"""
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
        
        # Determine winner
        if hybrid_detected >= max(tess_detected, easy_detected):
            winner = 'Hybrid'
        elif easy_detected > tess_detected:
            winner = 'EasyOCR'
        else:
            winner = 'Tesseract'
        
        metrics['comparison'] = {
            'winner': winner,
            'recommendation': '🏆 Hybrid (Tesseract + EasyOCR)' if winner == 'Hybrid' else f'🥇 {winner}'
        }
        
        # Print summary
        print(f'\n{"="*60}')
        print('📊 RESULTS SUMMARY')
        print(f'{"="*60}')
        print(f'Tesseract:  {tess_detected}/{total_fields} fields ({metrics["tesseract"]["accuracy"]}%)')
        print(f'EasyOCR:    {easy_detected}/{total_fields} fields ({metrics["easyocr"]["accuracy"]}%)')
        print(f'Hybrid:     {hybrid_detected}/{total_fields} fields ({metrics["hybrid"]["accuracy"]}%)')
        print(f'Winner:     {winner}')
        print(f'{"="*60}\n')
        
        # Prepare response
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
            # Merged recommendation: combined view with source metadata
            'merged': merge_ocr_results(tess_data, easy_data, hybrid_data),
            'metrics': metrics
        }

        # merged already populated via merge_ocr_results
        
        print('✅ Processing complete!\n')
        
        return jsonify(response)
        
    except Exception as e:
        print(f'\n❌ Error in process_image: {e}')
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500


@app.route('/api/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({
        'status': 'healthy',
        'timestamp': datetime.now().isoformat(),
        'upload_folder': app.config['UPLOAD_FOLDER'],
        'max_file_size': app.config['MAX_CONTENT_LENGTH']
    })


if __name__ == '__main__':
    print('='*60)
    print('🚀 Vaccine OCR Web Application - Production Ready')
    print('='*60)
    print(f'📂 Upload folder: {UPLOAD_FOLDER}')
    print(f'📦 Max file size: {MAX_FILE_SIZE / 1024 / 1024:.1f} MB')
    print(f'🌐 Server: http://localhost:5001')
    print(f'🧪 Test page: http://localhost:5001/test')
    print('='*60)
    print()
    
    app.run(debug=True, host='0.0.0.0', port=5001)