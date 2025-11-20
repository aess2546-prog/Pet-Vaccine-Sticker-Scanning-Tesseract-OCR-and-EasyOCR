// Vaccine OCR Web App - Frontend Logic (clean single-file)

let currentFile = null;
let accuracyChart = null;
let speedChart = null;

console.log('📜 Script loading...');

// Wait for DOM to be fully loaded before accessing elements
document.addEventListener('DOMContentLoaded', () => {
    console.log('✅ DOM Content Loaded');
    initializeApp();
});

function initializeApp() {
    const fileInput = document.getElementById('fileInput');
    const processBtn = document.getElementById('processBtn');

    if (!fileInput) {
        console.error('❌ fileInput not found! Please check `index.html`.');
        return;
    }

    // Attach listeners
    fileInput.addEventListener('change', handleFileSelect);
    if (processBtn) processBtn.addEventListener('click', processImage);

    console.log('✅ App initialized');
}

function handleFileSelect(e) {
    const file = e.target.files && e.target.files[0];
    if (!file) return;

    const allowedTypes = ['image/jpeg', 'image/jpg', 'image/png'];
    if (!allowedTypes.includes(file.type)) {
        alert('รองรับเฉพาะไฟล์ JPG และ PNG เท่านั้น');
        return;
    }
    if (file.size > 5 * 1024 * 1024) {
        alert('ไฟล์ต้องไม่เกิน 5MB');
        return;
    }

    currentFile = file;

    const reader = new FileReader();
    reader.onerror = () => {
        console.error('❌ FileReader error');
        alert('ไม่สามารถอ่านไฟล์ได้');
    };

    reader.onload = (ev) => {
        const previewImg = document.getElementById('previewImg');
        const uploadCard = document.getElementById('uploadCard');
        const imagePreview = document.getElementById('imagePreview');
        const results = document.getElementById('results');

        if (!previewImg) {
            console.error('❌ previewImg element not found');
            return;
        }

        previewImg.src = ev.target.result;
        if (uploadCard) uploadCard.style.display = 'none';
        if (imagePreview) imagePreview.style.display = 'block';
        if (results) results.style.display = 'none';
    };

    reader.readAsDataURL(file);
}

async function processImage() {
    if (!currentFile) {
        alert('กรุณาเลือกไฟล์');
        return;
    }

    const loading = document.getElementById('loading');
    const results = document.getElementById('results');
    if (loading) loading.style.display = 'block';
    if (results) results.style.display = 'none';

    const formData = new FormData();
    formData.append('file', currentFile);

    try {
        const response = await fetch('/api/process', { method: 'POST', body: formData });
        if (!response.ok) {
            const err = await response.text();
            throw new Error(`Server error ${response.status}: ${err}`);
        }
        const data = await response.json();
        if (loading) loading.style.display = 'none';
        displayResults(data);
    } catch (error) {
        console.error('❌ Process error:', error);
        alert('เกิดข้อผิดพลาด: ' + error.message);
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
        console.error('❌ results element not found');
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

    // Merged / Recommended
    setTextContent('mergedVaccineName', getValue(data, 'merged.data.vaccine_name') || getValue(data, 'merged.data.product_name'));
    setTextContent('mergedTradeName', getValue(data, 'merged.data.product_name'));
    setTextContent('mergedRegNo', getValue(data, 'merged.data.registration_number'));
    setTextContent('mergedSerial', getValue(data, 'merged.data.serial_number'));
    setTextContent('mergedMfg', getValue(data, 'merged.data.mfg_date'));
    setTextContent('mergedExp', getValue(data, 'merged.data.exp_date'));

    // Show sources/reasons compactly
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

    // Prefer per-side raw OCR output (unprocessed) if available; fall back to combined/raw formatted
    const tessLeftRaw = getValue(data, 'tesseract.raw_left') || getValue(data, 'tesseract.raw_output') || getValue(data, 'tesseract.formatted_output', '(ไม่มีข้อความ)');
    const tessRightRaw = getValue(data, 'tesseract.raw_right') || getValue(data, 'tesseract.raw_output') || getValue(data, 'tesseract.formatted_output', '(ไม่มีข้อความ)');

    const easyLeftRaw = getValue(data, 'easyocr.raw_left') || getValue(data, 'easyocr.raw_output') || getValue(data, 'easyocr.formatted_output', '(ไม่มีข้อความ)');
    const easyRightRaw = getValue(data, 'easyocr.raw_right') || getValue(data, 'easyocr.raw_output') || getValue(data, 'easyocr.formatted_output', '(ไม่มีข้อความ)');

    // Put raw text into the <pre> blocks so whitespace/line breaks are preserved
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
    createAccuracyChart(metrics);
    createSpeedChart(metrics);

    results.scrollIntoView({ behavior: 'smooth', block: 'start' });
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
        console.error('❌ Accuracy chart error', e);
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
        console.error('❌ Speed chart error', e);
    }
}

console.log('✅ Script loaded');