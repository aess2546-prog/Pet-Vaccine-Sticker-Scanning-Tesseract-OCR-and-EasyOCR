let currentFile = null;
let accuracyChart = null;
let speedChart = null;

console.log('กำลังโหลด...');

document.addEventListener('DOMContentLoaded', () => {
    console.log('DOM Content Loaded');
    initializeApp();
});

function initializeApp() {
    const fileInput = document.getElementById('fileInput');
    const uploadBox = document.getElementById('uploadBox');
    const uploadBtn = document.getElementById('uploadBtn');
    const changeImageBtn = document.getElementById('changeImageBtn');

    if (!fileInput) {
        console.error('fileInput not found! Please check `index.html`.');
        return;
    }

    fileInput.addEventListener('change', handleFileSelect);

    // การคลิกปุ่มอัปโหลด
    if (uploadBtn) {
        uploadBtn.addEventListener('click', (e) => {
            e.stopPropagation(); // ป้องกันไม่ให้เหตุการณ์ลอยไปยัง uploadBox
            fileInput.click();
        });
    }

    // การคลิกปุ่มเปลี่ยนรูปภาพ
    if (changeImageBtn) {
        changeImageBtn.addEventListener('click', () => {
            fileInput.click();
        });
    }

    // ฟังก์ชันลากและวาง
    if (uploadBox) {
        //คลิกที่พื้นที่กล่องอัปโหลด
        uploadBox.addEventListener('click', (e) => {
            // ให้ทำงานเมื่อไม่ได้คลิกที่ตัวปุ่มโดยตรงเท่านั้น
            if (uploadBtn && (e.target === uploadBtn || uploadBtn.contains(e.target))) {
                return;
            }
            fileInput.click();
        });

        // ป้องกันการลากตามค่าเริ่มต้น
        ['dragenter', 'dragover', 'dragleave', 'drop'].forEach(eventName => {
            uploadBox.addEventListener(eventName, preventDefaults, false);
            document.body.addEventListener(eventName, preventDefaults, false);
        });

        // ไฮไลต์พื้นที่วางไฟล์เมื่อมีการลากมาทับ
        ['dragenter', 'dragover'].forEach(eventName => {
            uploadBox.addEventListener(eventName, () => {
                uploadBox.classList.add('drag-over');
            }, false);
        });

        ['dragleave', 'drop'].forEach(eventName => {
            uploadBox.addEventListener(eventName, () => {
                uploadBox.classList.remove('drag-over');
            }, false);
        });

        // จัดการไฟล์ที่ถูกวาง
        uploadBox.addEventListener('drop', handleDrop, false);
    }

    console.log('App initialized with drag & drop');
}

function preventDefaults(e) {
    e.preventDefault();
    e.stopPropagation();
}

function handleDrop(e) {
    const dt = e.dataTransfer;
    const files = dt.files;

    if (files.length > 0) {
        const file = files[0];
        // ตรวจสอบความถูกต้องและประมวลผลไฟล์
        validateAndPreviewFile(file);
    }
}

function handleFileSelect(e) {
    const file = e.target.files && e.target.files[0];
    if (!file) return;
    validateAndPreviewFile(file);
}

function validateAndPreviewFile(file) {
    const allowedTypes = ['image/jpeg', 'image/jpg', 'image/png'];
    if (!allowedTypes.includes(file.type)) {
        showNotification('รองรับเฉพาะไฟล์ JPG และ PNG เท่านั้น', 'error');
        return;
    }
    if (file.size > 5 * 1024 * 1024) {
        showNotification('ไฟล์ต้องไม่เกิน 5MB', 'error');
        return;
    }

    currentFile = file;

    const reader = new FileReader();
    reader.onerror = () => {
        console.error('FileReader error');
        showNotification('ไม่สามารถอ่านไฟล์ได้', 'error');
    };

    reader.onload = (ev) => {
        const previewImg = document.getElementById('previewImg');
        const uploadBox = document.getElementById('uploadBox');
        const imagePreview = document.getElementById('imagePreview');
        const results = document.getElementById('results');
        const fileName = document.getElementById('fileName');
        const imageSize = document.getElementById('imageSize');

        if (!previewImg) {
            console.error('previewImg element not found');
            return;
        }

        previewImg.src = ev.target.result;
        if (fileName) fileName.textContent = file.name;
        if (imageSize) {
            const sizeMB = (file.size / (1024 * 1024)).toFixed(2);
            imageSize.textContent = `ขนาดไฟล์: ${sizeMB} MB`;
        }

        if (uploadBox) uploadBox.style.display = 'none';
        if (imagePreview) imagePreview.style.display = 'block';
        if (results) results.style.display = 'none';

        showNotification('อัปโหลดรูปภาพสำเร็จ!', 'success');
    };

    reader.readAsDataURL(file);
}

function showNotification(message, type = 'info') {
    // การแจ้งเตือน
    const styles = {
        success: { bg: '#00b894', icon: '✓' },
        error: { bg: '#d63031', icon: '✗' },
        info: { bg: '#0984e3', icon: 'ℹ' }
    };

    const style = styles[type] || styles.info;

    // สร้าง element ของการแจ้งเตือน
    const notification = document.createElement('div');
    notification.style.cssText = `
        position: fixed;
        top: 20px;
        right: 20px;
        background: ${style.bg};
        color: white;
        padding: 16px 24px;
        border-radius: 12px;
        box-shadow: 0 4px 12px rgba(0,0,0,0.15);
        z-index: 10000;
        font-weight: 600;
        animation: slideIn 0.3s ease-out;
    `;
    notification.textContent = `${style.icon} ${message}`;

    document.body.appendChild(notification);

    setTimeout(() => {
        notification.style.animation = 'slideOut 0.3s ease-out';
        setTimeout(() => notification.remove(), 300);
    }, 3000);
}

async function processImage() {
    if (!currentFile) {
        showNotification('กรุณาเลือกไฟล์', 'error');
        return;
    }

    const loading = document.getElementById('loading');
    const results = document.getElementById('results');
    
    if (loading) loading.style.display = 'block';
    if (results) results.style.display = 'none';

    const formData = new FormData();
    formData.append('file', currentFile);

    try {
        const response = await fetch('/api/process', { 
            method: 'POST', 
            body: formData 
        });
        
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        
        const data = await response.json();
        
        if (loading) loading.style.display = 'none';
        
        if (data.success) {
            displayResults(data);
        } else {
            throw new Error(data.error || 'Unknown error');
        }
        
    } catch (error) {
        console.error('Process error:', error);
        showNotification('เกิดข้อผิดพลาด: ' + error.message, 'error');
        if (loading) loading.style.display = 'none';
    }
}

function getValue(obj, path, defaultValue = 'ไม่พบ') {
    try {
        if (!obj) return defaultValue;
        const keys = path.split('.');
        let value = obj;
        for (const key of keys) {
            if (value && typeof value === 'object' && key in value) value = value[key];
            else return defaultValue;
        }
        return value ?? defaultValue;
    } catch (e) {
        console.warn('getValue error:', path, e);
        return defaultValue;
    }
}

function setTextContent(id, value) {
    const el = document.getElementById(id);
    if (el) el.textContent = value;
}

function displayResults(data) {
    const results = document.getElementById('results');
    if (!results) {
        console.error('results element not found');
        return;
    }
    results.style.display = 'block';

    setTextContent('tessVaccineName', getValue(data, 'tesseract.data.vaccine_name') || getValue(data, 'tesseract.data.product_name'));
    setTextContent('tessTradeName', getValue(data, 'tesseract.data.product_name'));
    setTextContent('tessRegNo', getValue(data, 'tesseract.data.registration_number'));
    setTextContent('tessSerial', getValue(data, 'tesseract.data.serial_number'));
    setTextContent('tessMfg', getValue(data, 'tesseract.data.mfg_date'));
    setTextContent('tessExp', getValue(data, 'tesseract.data.exp_date'));
    setTextContent('tessTime', getValue(data, 'metrics.tesseract.processing_time', 0) + 's');

    setTextContent('easyVaccineName', getValue(data, 'easyocr.data.vaccine_name') || getValue(data, 'easyocr.data.product_name'));
    setTextContent('easyTradeName', getValue(data, 'easyocr.data.product_name'));
    setTextContent('easyRegNo', getValue(data, 'easyocr.data.registration_number'));
    setTextContent('easySerial', getValue(data, 'easyocr.data.serial_number'));
    setTextContent('easyMfg', getValue(data, 'easyocr.data.mfg_date'));
    setTextContent('easyExp', getValue(data, 'easyocr.data.exp_date'));
    setTextContent('easyTime', getValue(data, 'metrics.easyocr.processing_time', 0) + 's');

    // รวมรายการ / คำแนะนำ
    setTextContent('mergedVaccineName', getValue(data, 'merged.data.vaccine_name') || getValue(data, 'merged.data.product_name'));
    setTextContent('mergedTradeName', getValue(data, 'merged.data.product_name'));
    setTextContent('mergedRegNo', getValue(data, 'merged.data.registration_number'));
    setTextContent('mergedSerial', getValue(data, 'merged.data.serial_number'));
    setTextContent('mergedMfg', getValue(data, 'merged.data.mfg_date'));
    setTextContent('mergedExp', getValue(data, 'merged.data.exp_date'));

    // สรุปแหล่งที่มาและเหตุผล
    try {
        const sources = getValue(data, 'merged.sources', {});
        const parts = [];
        for (const k of ['vaccine_name','product_name','registration_number','serial_number','mfg_date','exp_date']) {
            if (sources[k]) parts.push(`${k}: ${sources[k].source} (${sources[k].reason})`);
        }
        setTextContent('mergedSources', parts.join(' | '));
    } catch (e) {
        setTextContent('mergedSources', '-');
    }

    const tessAcc = getValue(data, 'metrics.tesseract.accuracy', 0);
    const easyAcc = getValue(data, 'metrics.easyocr.accuracy', 0);
    const tessSpeed = getValue(data, 'metrics.tesseract.processing_time', 0);
    const easySpeed = getValue(data, 'metrics.easyocr.processing_time', 0);

    setTextContent('tessAccuracy', typeof tessAcc === 'number' ? tessAcc.toFixed(0) + '%' : tessAcc);
    setTextContent('easyAccuracy', typeof easyAcc === 'number' ? easyAcc.toFixed(0) + '%' : easyAcc);
    setTextContent('tessSpeed', typeof tessSpeed === 'number' ? tessSpeed.toFixed(2) + 's' : tessSpeed);
    setTextContent('easySpeed', typeof easySpeed === 'number' ? easySpeed.toFixed(2) + 's' : easySpeed);

    const winner = getValue(data, 'metrics.comparison.recommendation') || getValue(data, 'metrics.comparison.winner', 'Hybrid');
    setTextContent('winnerName', winner);

    const tessLeftRaw = getValue(data, 'tesseract.raw_left') || getValue(data, 'tesseract.raw_output') || getValue(data, 'tesseract.formatted_output', '(ไม่มีข้อความ)');
    const tessRightRaw = getValue(data, 'tesseract.raw_right') || getValue(data, 'tesseract.raw_output') || getValue(data, 'tesseract.formatted_output', '(ไม่มีข้อความ)');

    const easyLeftRaw = getValue(data, 'easyocr.raw_left') || getValue(data, 'easyocr.raw_output') || getValue(data, 'easyocr.formatted_output', '(ไม่มีข้อความ)');
    const easyRightRaw = getValue(data, 'easyocr.raw_right') || getValue(data, 'easyocr.raw_output') || getValue(data, 'easyocr.formatted_output', '(ไม่มีข้อความ)');

    // นำข้อความดิบใส่ <pre> เพื่อเก็บรูปแบบและเว้นวรรคเดิม
    const tessLeftEl = document.getElementById('tessLeftRaw');
    const tessRightEl = document.getElementById('tessRightRaw');
    const easyLeftEl = document.getElementById('easyLeftRaw');
    const easyRightEl = document.getElementById('easyRightRaw');

    if (tessLeftEl) tessLeftEl.textContent = tessLeftRaw;
    if (tessRightEl) tessRightEl.textContent = tessRightRaw;
    if (easyLeftEl) easyLeftEl.textContent = easyLeftRaw;
    if (easyRightEl) easyRightEl.textContent = easyRightRaw;

    if (data.images) {
        const original = document.getElementById('originalImage');
        const left = document.getElementById('leftPreprocessed');
        const right = document.getElementById('rightPreprocessed');
        if (original && data.images.original) original.src = data.images.original;
        if (left && data.images.left_preprocessed) left.src = data.images.left_preprocessed;
        if (right && data.images.right_preprocessed) right.src = data.images.right_preprocessed;
    }

    const metrics = data.metrics || {};

    displayMergeQuality(metrics.merge_quality || {});
    displayFieldAccuracy(metrics.field_level_accuracy || {});
    displayMergeDecisions(metrics.merge_decisions || {});

    results.scrollIntoView({ behavior: 'smooth', block: 'start' });
}

function displayMergeQuality(mergeQuality) {
    setTextContent('mergeQualityTess', mergeQuality.tesseract_accuracy + '%' || '0%');
    setTextContent('mergeQualityEasy', mergeQuality.easyocr_accuracy + '%' || '0%');
    setTextContent('mergeQualityMerged', mergeQuality.merged_accuracy + '%' || '0%');

    const improvement = mergeQuality.improvement || 0;
    const improvementText = improvement >= 0 ? `+${improvement}%` : `${improvement}%`;
    setTextContent('mergeQualityImprovement', improvementText);
}

function displayFieldAccuracy(fieldAccuracy) {
    const container = document.getElementById('fieldAccuracyBars');
    if (!container) return;

    const fieldNames = {
        'vaccine_name': 'ชื่อวัคซีน',
        'product_name': 'ชื่อการค้า',
        'registration_number': 'เลขทะเบียน',
        'serial_number': 'Serial Number',
        'mfg_date': 'วันที่ผลิต',
        'exp_date': 'วันหมดอายุ'
    };

    let html = '';
    for (const [field, label] of Object.entries(fieldNames)) {
        const data = fieldAccuracy[field] || {};
        const tessAcc = Math.round(data.tesseract || 0);
        const easyAcc = Math.round(data.easyocr || 0);

        html += `
            <div class="field-accuracy-item">
                <div class="field-label">${label}</div>
                <div class="engine-bars">
                    <div class="engine-row">
                        <div class="engine-name">Tesseract</div>
                        <div class="bar-track">
                            <div class="bar-fill bar-tesseract" style="width: ${tessAcc}%"></div>
                        </div>
                        <div class="accuracy-value">${tessAcc}%</div>
                    </div>
                    <div class="engine-row">
                        <div class="engine-name">EasyOCR</div>
                        <div class="bar-track">
                            <div class="bar-fill bar-easyocr" style="width: ${easyAcc}%"></div>
                        </div>
                        <div class="accuracy-value">${easyAcc}%</div>
                    </div>
                </div>
            </div>
        `;
    }

    container.innerHTML = html;
}

function displayMergeDecisions(mergeDecisions) {
    const container = document.getElementById('mergeDecisionsTable');
    if (!container) return;

    const fieldNames = {
        'vaccine_name': 'ชื่อวัคซีน',
        'product_name': 'ชื่อการค้า',
        'registration_number': 'เลขทะเบียน',
        'serial_number': 'Serial Number',
        'mfg_date': 'วันที่ผลิต',
        'exp_date': 'วันหมดอายุ'
    };

    let html = `
        <table class="decision-table">
            <thead>
                <tr>
                    <th>ฟิลด์</th>
                    <th>Tesseract</th>
                    <th>EasyOCR</th>
                    <th>เลือก</th>
                    <th>แหล่งที่มา</th>
                    <th>ตรงกัน?</th>
                </tr>
            </thead>
            <tbody>
    `;

    for (const [field, label] of Object.entries(fieldNames)) {
        const data = mergeDecisions[field] || {};
        const agree = data.engines_agree ? 'ใช่' : 'ไม่';
        const agreeClass = data.engines_agree ? 'agree-yes' : 'agree-no';

        html += `
            <tr class="decision-row">
                <td><strong>${label}</strong></td>
                <td>${data.tesseract || '-'}</td>
                <td>${data.easyocr || '-'}</td>
                <td><strong>${data.selected || '-'}</strong></td>
                <td><span class="source-badge">${data.source || '-'}</span></td>
                <td><span class="agree-badge ${agreeClass}">${agree}</span></td>
            </tr>
        `;
    }

    html += `
            </tbody>
        </table>
    `;

    container.innerHTML = html;
}

function createAccuracyChart(metrics) {
    try {
        const ctx = document.getElementById('accuracyChart');
        if (!ctx) return;
        if (accuracyChart) accuracyChart.destroy();

        const tessAcc = getValue(metrics, 'tesseract.accuracy', 0);
        const easyAcc = getValue(metrics, 'easyocr.accuracy', 0);
        const hybridAcc = getValue(metrics, 'hybrid.accuracy', 0);

        accuracyChart = new Chart(ctx, {
            type: 'bar',
            data: {
                labels: ['Tesseract', 'EasyOCR', 'Hybrid'],
                datasets: [{
                    label: 'ความแม่นยำ (%)',
                    data: [tessAcc, easyAcc, hybridAcc],
                    backgroundColor: ['rgba(9,132,227,0.8)','rgba(225,112,85,0.8)','rgba(72,187,120,0.8)'],
                    borderColor: ['rgba(9,132,227,1)','rgba(225,112,85,1)','rgba(56,161,105,1)'],
                    borderWidth: 2,
                    borderRadius: 8
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: true,
                plugins: { legend: { display: false } },
                scales: { y: { beginAtZero: true, max: 100 } }
            }
        });
    } catch (e) {
        console.error('Accuracy chart error', e);
    }
}

function createSpeedChart(metrics) {
    try {
        const ctx = document.getElementById('speedChart');
        if (!ctx) return;
        if (speedChart) speedChart.destroy();

        const tessSpeed = getValue(metrics, 'tesseract.processing_time', 0);
        const easySpeed = getValue(metrics, 'easyocr.processing_time', 0);
        const hybridSpeed = getValue(metrics, 'hybrid.processing_time', 0);

        speedChart = new Chart(ctx, {
            type: 'bar',
            data: {
                labels: ['Tesseract', 'EasyOCR', 'Hybrid'],
                datasets: [{
                    label: 'เวลา (วินาที)',
                    data: [tessSpeed, easySpeed, hybridSpeed],
                    backgroundColor: ['rgba(85,239,196,0.8)','rgba(253,121,168,0.8)','rgba(129,140,248,0.8)'],
                    borderColor: ['rgba(0,184,148,1)','rgba(232,67,147,1)','rgba(99,102,241,1)'],
                    borderWidth: 2,
                    borderRadius: 8
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: true,
                plugins: { legend: { display: false } },
                scales: { y: { beginAtZero: true } }
            }
        });
    } catch (e) {
        console.error('Speed chart error', e);
    }
}

// Toggle Raw Text Section
function toggleRawText() {
    const content = document.getElementById('rawTextContent');
    const toggleIcon = document.getElementById('rawTextToggle');

    if (content && toggleIcon) {
        if (content.style.display === 'none' || content.style.display === '') {
            content.style.display = 'grid';
            toggleIcon.textContent = '▲';
            toggleIcon.classList.add('rotated');
        } else {
            content.style.display = 'none';
            toggleIcon.textContent = '▼';
            toggleIcon.classList.remove('rotated');
        }
    }
}

console.log('Script loaded');