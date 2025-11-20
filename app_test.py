"""
Preprocessing Test App with OCR Scanning
ปรับ parameters → ดูรูป → สแกน OCR ทันที
"""

from flask import Flask, render_template_string, request, jsonify, send_from_directory
from flask_cors import CORS
import os
import cv2
import time
import json
import numpy as np
from datetime import datetime
from werkzeug.utils import secure_filename
import pytesseract

# EasyOCR
try:
    import easyocr
    EASYOCR_AVAILABLE = True
    _reader = None
except ImportError:
    EASYOCR_AVAILABLE = False
    _reader = None

app = Flask(__name__)
CORS(app)

# Configuration
UPLOAD_FOLDER = os.path.join(os.path.dirname(__file__), 'uploads_test')
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 5 * 1024 * 1024


# OCR Functions
def get_easyocr_reader():
    global _reader
    if _reader is None and EASYOCR_AVAILABLE:
        try:
            _reader = easyocr.Reader(['en'], gpu=False, verbose=False)
        except:
            pass
    return _reader


def ocr_tesseract(image: np.ndarray) -> str:
    try:
        config = '--psm 6 --oem 3'
        text = pytesseract.image_to_string(image, lang='eng', config=config)
        return text.strip()
    except Exception as e:
        return f'Error: {e}'


def ocr_easyocr(image: np.ndarray) -> str:
    try:
        reader = get_easyocr_reader()
        if reader is None:
            return 'EasyOCR not available'
        results = reader.readtext(image, detail=0, paragraph=True)
        return ' '.join(results)
    except Exception as e:
        return f'Error: {e}'


# Preprocessing Functions
def detect_split_point(image: np.ndarray) -> int:
    height, width = image.shape[:2]
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY) if len(image.shape) == 3 else image
    
    brightness = []
    for x in range(width):
        column = gray[int(height*0.2):int(height*0.8), x]
        brightness.append(np.mean(column))
    
    max_drop, split_x = 0, int(width * 0.65)
    window_size = int(width * 0.05)
    
    for x in range(int(width*0.5), int(width*0.8)):
        if x < window_size or x >= width - window_size:
            continue
        left_avg = np.mean(brightness[max(0, x-window_size):x])
        right_avg = np.mean(brightness[x:min(width, x+window_size)])
        if (drop := left_avg - right_avg) > max_drop:
            max_drop, split_x = drop, x
    
    return split_x


def split_image(image: np.ndarray):
    split_x = detect_split_point(image)
    return image[:, :split_x], image[:, split_x:]


def rotate_90(image: np.ndarray) -> np.ndarray:
    return cv2.rotate(image, cv2.ROTATE_90_CLOCKWISE)


def save_image(image: np.ndarray, filepath: str) -> bool:
    try:
        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        if image.dtype != np.uint8:
            image = cv2.normalize(image, None, 0, 255, cv2.NORM_MINMAX).astype(np.uint8)
        return cv2.imwrite(filepath, image)
    except:
        return False


# HTML Template with OCR Buttons
HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="th">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>🧪 ทดสอบ Preprocessing + OCR</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: 'Segoe UI', sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            padding: 20px;
        }
        .container { max-width: 1400px; margin: 0 auto; }
        .header { text-align: center; color: white; margin-bottom: 30px; }
        .header h1 { font-size: 36px; margin-bottom: 10px; }
        .card {
            background: white;
            border-radius: 20px;
            padding: 30px;
            box-shadow: 0 5px 20px rgba(0,0,0,0.2);
            margin-bottom: 30px;
        }
        .upload-area {
            border: 3px dashed #cbd5e0;
            border-radius: 15px;
            padding: 40px;
            text-align: center;
            background: #f7fafc;
        }
        .btn {
            padding: 12px 30px;
            border: none;
            border-radius: 25px;
            font-size: 16px;
            font-weight: 600;
            cursor: pointer;
            transition: all 0.3s;
            margin: 5px;
        }
        .btn-primary { background: linear-gradient(135deg, #667eea, #764ba2); color: white; }
        .btn-process { background: linear-gradient(135deg, #48bb78, #38a169); color: white; }
        .btn-ocr-tess { background: linear-gradient(135deg, #4299e1, #3182ce); color: white; }
        .btn-ocr-easy { background: linear-gradient(135deg, #ed8936, #dd6b20); color: white; }
        .btn:hover { transform: translateY(-2px); box-shadow: 0 5px 15px rgba(0,0,0,0.3); }
        .control-row {
            display: grid;
            grid-template-columns: repeat(3, 1fr);
            gap: 20px;
            margin-bottom: 20px;
        }
        .control-group label {
            display: block;
            margin-bottom: 8px;
            font-weight: 600;
            color: #4a5568;
        }
        input[type="range"] { width: 100%; }
        .loading {
            text-align: center;
            padding: 40px;
            background: white;
            border-radius: 20px;
        }
        .spinner {
            width: 50px;
            height: 50px;
            border: 5px solid #e2e8f0;
            border-top-color: #667eea;
            border-radius: 50%;
            animation: spin 1s linear infinite;
            margin: 0 auto 20px;
        }
        @keyframes spin { to { transform: rotate(360deg); } }
        .stats {
            background: #f7fafc;
            border-radius: 12px;
            padding: 20px;
            margin-bottom: 20px;
        }
        .stat-row {
            display: flex;
            justify-content: space-between;
            padding: 8px 0;
            border-bottom: 1px solid #e2e8f0;
        }
        .image-grid {
            display: grid;
            grid-template-columns: repeat(3, 1fr);
            gap: 20px;
            margin-bottom: 20px;
        }
        .image-box {
            background: #f7fafc;
            border-radius: 12px;
            padding: 15px;
            text-align: center;
        }
        .image-box img {
            max-width: 100%;
            border-radius: 8px;
            box-shadow: 0 2px 8px rgba(0,0,0,0.1);
        }
        .ocr-buttons {
            text-align: center;
            margin: 20px 0;
        }
        .ocr-results {
            display: grid;
            grid-template-columns: repeat(2, 1fr);
            gap: 20px;
            margin-top: 20px;
        }
        .ocr-box {
            background: #f7fafc;
            border-radius: 12px;
            padding: 20px;
            border: 2px solid #e2e8f0;
        }
        .ocr-box h3 {
            margin-bottom: 15px;
            padding: 10px;
            border-radius: 8px;
            color: white;
        }
        .ocr-box.tess h3 { background: linear-gradient(135deg, #4299e1, #3182ce); }
        .ocr-box.easy h3 { background: linear-gradient(135deg, #ed8936, #dd6b20); }
        .ocr-box pre {
            background: #2d3436;
            color: #00ff00;
            padding: 15px;
            border-radius: 8px;
            font-size: 13px;
            line-height: 1.6;
            max-height: 400px;
            overflow-y: auto;
            white-space: pre-wrap;
            font-family: 'Courier New', monospace;
        }
        .ocr-box .time {
            margin-top: 10px;
            text-align: right;
            color: #718096;
            font-size: 13px;
        }
    </style>
</head>
<body>
    <div class="container">
        <header class="header">
            <h1>🧪 ทดสอบ Preprocessing + OCR</h1>
            <p>ปรับค่า → ดูรูป → สแกนด้วย OCR ทันที</p>
        </header>

        <div class="card">
            <div class="upload-area">
                <h3>เลือกรูปวัคซีน</h3>
                <input type="file" id="fileInput" accept="image/*" style="display:none;">
                <button class="btn btn-primary" onclick="document.getElementById('fileInput').click()">เลือกรูป</button>
                <button class="btn btn-process" id="processBtn" onclick="processImage()" style="display:none;">ประมวลผล</button>
            </div>
        </div>

        <div class="card" id="controls" style="display:none;">
            <h2>⚙️ ตั้งค่า Preprocessing</h2>
            <div class="control-row">
                <div class="control-group">
                    <label>Scale: <span id="scaleValue">8</span>x</label>
                    <input type="range" id="scaleSlider" min="6" max="15" value="8" 
                           oninput="document.getElementById('scaleValue').textContent=this.value">
                </div>
                <div class="control-group">
                    <label>Alpha (Contrast): <span id="alphaValue">1.5</span></label>
                    <input type="range" id="alphaSlider" min="1.0" max="4.0" step="0.1" value="1.5"
                           oninput="document.getElementById('alphaValue').textContent=this.value">
                </div>
                <div class="control-group">
                    <label>Beta (Brightness): <span id="betaValue">0</span></label>
                    <input type="range" id="betaSlider" min="0" max="60" value="0"
                           oninput="document.getElementById('betaValue').textContent=this.value">
                </div>
            </div>
            <div class="control-row">
                <div class="control-group">
                    <label>Block Size: <span id="blockValue">7</span></label>
                    <input type="range" id="blockSlider" min="3" max="31" step="2" value="7"
                           oninput="document.getElementById('blockValue').textContent=this.value">
                </div>
                <div class="control-group">
                    <label>C Value: <span id="cValue">1</span></label>
                    <input type="range" id="cSlider" min="0" max="15" value="1"
                           oninput="document.getElementById('cValue').textContent=this.value">
                </div>
                <div class="control-group">
                    <button class="btn btn-process" onclick="processImage()" style="width:100%;margin-top:25px;">🔄 ประมวลผลใหม่</button>
                </div>
            </div>
        </div>

        <div class="loading" id="loading" style="display:none;">
            <div class="spinner"></div>
            <p>กำลังประมวลผล...</p>
        </div>

        <div class="card" id="results" style="display:none;">
            <h2>📊 ผลลัพธ์</h2>
            
            <div class="stats">
                <div class="stat-row">
                    <span>White Pixels:</span>
                    <span id="whitePercent">-</span>
                </div>
                <div class="stat-row">
                    <span>Method:</span>
                    <span id="methodUsed">-</span>
                </div>
                <div class="stat-row">
                    <span>Size:</span>
                    <span id="imageSize">-</span>
                </div>
                <div class="stat-row">
                    <span>Time:</span>
                    <span id="processTime">-</span>
                </div>
            </div>

            <div class="image-grid">
                <div class="image-box">
                    <h3>Original</h3>
                    <img id="originalImg" src="">
                </div>
                <div class="image-box">
                    <h3>Right Raw</h3>
                    <img id="rightRawImg" src="">
                </div>
                <div class="image-box">
                    <h3>Right Processed</h3>
                    <img id="rightProcessedImg" src="">
                </div>
            </div>

            <div class="ocr-buttons">
                <button class="btn btn-ocr-tess" onclick="scanOCR('tesseract', 'left')">🔷 Scan Left (Tesseract)</button>
                <button class="btn btn-ocr-tess" onclick="scanOCR('tesseract', 'right')">🔷 Scan Right (Tesseract)</button>
                <button class="btn btn-ocr-easy" onclick="scanOCR('easyocr', 'left')">🔶 Scan Left (EasyOCR)</button>
                <button class="btn btn-ocr-easy" onclick="scanOCR('easyocr', 'right')">🔶 Scan Right (EasyOCR)</button>
            </div>

            <div class="ocr-results" id="ocrResults" style="display:none;">
                <!-- Tesseract Left -->
                <div class="ocr-box tess">
                    <h3>🔷 Tesseract - Left Region</h3>
                    <pre id="tessLeftText">(ยังไม่ได้สแกน)</pre>
                    <div class="time" id="tessLeftTime">-</div>
                </div>
                
                <!-- Tesseract Right -->
                <div class="ocr-box tess">
                    <h3>🔷 Tesseract - Right Region</h3>
                    <pre id="tessRightText">(ยังไม่ได้สแกน)</pre>
                    <div class="time" id="tessRightTime">-</div>
                </div>
                
                <!-- EasyOCR Left -->
                <div class="ocr-box easy">
                    <h3>🔶 EasyOCR - Left Region</h3>
                    <pre id="easyLeftText">(ยังไม่ได้สแกน)</pre>
                    <div class="time" id="easyLeftTime">-</div>
                </div>
                
                <!-- EasyOCR Right -->
                <div class="ocr-box easy">
                    <h3>🔶 EasyOCR - Right Region</h3>
                    <pre id="easyRightText">(ยังไม่ได้สแกน)</pre>
                    <div class="time" id="easyRightTime">-</div>
                </div>
            </div>
        </div>
    </div>

    <script>
        let currentFile = null;
        let currentImages = {};

        document.getElementById('fileInput').addEventListener('change', (e) => {
            currentFile = e.target.files[0];
            if (currentFile) {
                document.getElementById('processBtn').style.display = 'inline-block';
                document.getElementById('controls').style.display = 'block';
            }
        });

        async function processImage() {
            if (!currentFile) return alert('กรุณาเลือกไฟล์');

            document.getElementById('loading').style.display = 'block';
            document.getElementById('results').style.display = 'none';

            const params = {
                scale: parseInt(document.getElementById('scaleSlider').value),
                alpha: parseFloat(document.getElementById('alphaSlider').value),
                beta: parseInt(document.getElementById('betaSlider').value),
                block_size: parseInt(document.getElementById('blockSlider').value),
                c_value: parseInt(document.getElementById('cSlider').value)
            };

            const formData = new FormData();
            formData.append('file', currentFile);
            formData.append('params', JSON.stringify(params));

            try {
                const response = await fetch('/api/test', { method: 'POST', body: formData });
                if (!response.ok) throw new Error('เกิดข้อผิดพลาด');

                const data = await response.json();
                currentImages = data.images;
                
                document.getElementById('loading').style.display = 'none';
                displayResults(data);

            } catch (error) {
                alert('Error: ' + error.message);
                document.getElementById('loading').style.display = 'none';
            }
        }

        function displayResults(data) {
            document.getElementById('results').style.display = 'block';
            document.getElementById('whitePercent').textContent = data.white_percent.toFixed(1) + '%';
            document.getElementById('methodUsed').textContent = data.method;
            document.getElementById('imageSize').textContent = data.image_size[0] + ' x ' + data.image_size[1];
            document.getElementById('processTime').textContent = data.processing_time.toFixed(2) + 's';
            document.getElementById('originalImg').src = data.images.original;
            document.getElementById('rightRawImg').src = data.images.right_raw;
            document.getElementById('rightProcessedImg').src = data.images.right_processed;
            
            // Reset OCR results
            document.getElementById('tessLeftText').textContent = '(ยังไม่ได้สแกน)';
            document.getElementById('tessRightText').textContent = '(ยังไม่ได้สแกน)';
            document.getElementById('easyLeftText').textContent = '(ยังไม่ได้สแกน)';
            document.getElementById('easyRightText').textContent = '(ยังไม่ได้สแกน)';
            document.getElementById('tessLeftTime').textContent = '-';
            document.getElementById('tessRightTime').textContent = '-';
            document.getElementById('easyLeftTime').textContent = '-';
            document.getElementById('easyRightTime').textContent = '-';
            document.getElementById('ocrResults').style.display = 'grid';
            
            document.getElementById('results').scrollIntoView({ behavior: 'smooth' });
        }

        async function scanOCR(engine, region) {
            if (!currentImages || !currentImages[region + '_processed']) {
                alert('กรุณาประมวลผลรูปก่อน');
                return;
            }

            const textId = engine === 'tesseract' ? 
                (region === 'left' ? 'tessLeftText' : 'tessRightText') :
                (region === 'left' ? 'easyLeftText' : 'easyRightText');
            
            const timeId = engine === 'tesseract' ? 
                (region === 'left' ? 'tessLeftTime' : 'tessRightTime') :
                (region === 'left' ? 'easyLeftTime' : 'easyRightTime');
            
            const textBox = document.getElementById(textId);
            const timeBox = document.getElementById(timeId);
            
            textBox.textContent = '⏳ กำลังสแกน...';
            timeBox.textContent = '-';

            try {
                const response = await fetch('/api/ocr', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        image_url: currentImages[region + '_processed'],
                        engine: engine
                    })
                });

                if (!response.ok) throw new Error('OCR failed');

                const data = await response.json();
                textBox.textContent = data.text || '(ไม่พบข้อความ)';
                timeBox.textContent = `⏱️ ${data.processing_time.toFixed(2)}s`;

            } catch (error) {
                textBox.textContent = '❌ Error: ' + error.message;
                timeBox.textContent = '-';
            }
        }
    </script>
</body>
</html>
"""


@app.route('/')
def index():
    return render_template_string(HTML_TEMPLATE)


@app.route('/uploads_test/<path:filename>')
def uploaded_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)


@app.route('/api/test', methods=['POST'])
def test_preprocessing():
    try:
        file = request.files['file']
        params = json.loads(request.form.get('params', '{}'))
        
        scale = params.get('scale', 8)
        alpha = params.get('alpha', 1.5)
        beta = params.get('beta', 0)
        block_size = params.get('block_size', 7)
        c_value = params.get('c_value', 1)
        
        print(f'\n🔧 scale={scale}, α={alpha}, β={beta}, block={block_size}, C={c_value}')
        
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = secure_filename(file.filename)
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], f'{timestamp}_{filename}')
        file.save(filepath)
        
        image = cv2.imread(filepath)
        left, right = split_image(image)
        
        start_time = time.time()
        
        # Process LEFT region
        h_l, w_l = left.shape[:2]
        left_scaled = cv2.resize(left, (w_l*2, h_l*2), interpolation=cv2.INTER_CUBIC)
        left_gray = cv2.cvtColor(left_scaled, cv2.COLOR_BGR2GRAY) if len(left_scaled.shape) == 3 else left_scaled
        kernel = np.array([[0, -1, 0], [-1, 5, -1], [0, -1, 0]])
        left_sharp = cv2.filter2D(left_gray, -1, kernel)
        left_enhanced = cv2.convertScaleAbs(left_sharp, alpha=1.2, beta=10)
        _, left_binary = cv2.threshold(left_enhanced, 128, 255, cv2.THRESH_BINARY)
        left_final = cv2.medianBlur(left_binary, 3)
        
        # Process RIGHT region
        h_r, w_r = right.shape[:2]
        right_scaled = cv2.resize(right, (w_r*scale, h_r*scale), interpolation=cv2.INTER_CUBIC)
        right_rotated = rotate_90(right_scaled)
        right_gray = cv2.cvtColor(right_rotated, cv2.COLOR_BGR2GRAY) if len(right_rotated.shape) == 3 else right_rotated
        right_inverted = cv2.bitwise_not(right_gray)
        right_bilateral = cv2.bilateralFilter(right_inverted, 9, 75, 75)
        clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8,8))
        right_clahe = clahe.apply(right_bilateral)
        right_enhanced = cv2.convertScaleAbs(right_clahe, alpha=alpha, beta=beta)
        right_binary = cv2.adaptiveThreshold(right_enhanced, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
                                             cv2.THRESH_BINARY, blockSize=block_size, C=c_value)
        
        white_percent = (right_binary == 255).sum() / right_binary.size * 100
        
        right_denoised = cv2.medianBlur(right_binary, 3)
        kernel_morph = np.ones((2,2), np.uint8)
        right_opened = cv2.morphologyEx(right_denoised, cv2.MORPH_OPEN, kernel_morph, iterations=1)
        right_final = cv2.morphologyEx(right_opened, cv2.MORPH_CLOSE, kernel_morph, iterations=1)
        
        processing_time = time.time() - start_time
        
        print(f'   White: {white_percent:.1f}%, Time: {processing_time:.2f}s')
        
        # Save images
        original_path = os.path.join(app.config['UPLOAD_FOLDER'], f'{timestamp}_original.png')
        left_raw_path = os.path.join(app.config['UPLOAD_FOLDER'], f'{timestamp}_left_raw.png')
        left_proc_path = os.path.join(app.config['UPLOAD_FOLDER'], f'{timestamp}_left_processed.png')
        right_raw_path = os.path.join(app.config['UPLOAD_FOLDER'], f'{timestamp}_right_raw.png')
        right_proc_path = os.path.join(app.config['UPLOAD_FOLDER'], f'{timestamp}_right_processed.png')
        
        save_image(image, original_path)
        save_image(left, left_raw_path)
        save_image(left_final, left_proc_path)
        save_image(right, right_raw_path)
        save_image(right_final, right_proc_path)
        
        return jsonify({
            'success': True,
            'white_percent': white_percent,
            'method': f'Adaptive (α={alpha}, β={beta}, block={block_size}, C={c_value})',
            'image_size': [right_final.shape[0], right_final.shape[1]],
            'processing_time': processing_time,
            'images': {
                'original': f'/uploads_test/{timestamp}_original.png',
                'left_raw': f'/uploads_test/{timestamp}_left_raw.png',
                'left_processed': f'/uploads_test/{timestamp}_left_processed.png',
                'right_raw': f'/uploads_test/{timestamp}_right_raw.png',
                'right_processed': f'/uploads_test/{timestamp}_right_processed.png'
            }
        })
        
    except Exception as e:
        print(f'Error: {e}')
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500


@app.route('/api/ocr', methods=['POST'])
def scan_ocr():
    try:
        data = request.json
        image_url = data.get('image_url')
        engine = data.get('engine', 'tesseract')
        
        # Extract filename from URL
        filename = image_url.split('/')[-1]
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        
        if not os.path.exists(filepath):
            return jsonify({'error': 'Image not found'}), 404
        
        image = cv2.imread(filepath)
        if image is None:
            return jsonify({'error': 'Failed to load image'}), 400
        
        start_time = time.time()
        
        if engine == 'tesseract':
            text = ocr_tesseract(image)
        else:
            text = ocr_easyocr(image)
        
        processing_time = time.time() - start_time
        
        print(f'   {engine.upper()}: {len(text)} chars, {processing_time:.2f}s')
        
        return jsonify({
            'success': True,
            'text': text,
            'processing_time': processing_time
        })
        
    except Exception as e:
        print(f'OCR Error: {e}')
        return jsonify({'error': str(e)}), 500


if __name__ == '__main__':
    print('🚀 Starting Preprocessing Test App with OCR...')
    print('🌐 Open: http://localhost:5002')
    print('='*60)
    app.run(debug=True, host='0.0.0.0', port=5002)