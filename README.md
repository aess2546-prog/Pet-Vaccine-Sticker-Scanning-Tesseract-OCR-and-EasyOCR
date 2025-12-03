ระบบสแกนสติกเกอร์วัคซีนสัตว์เลี้ยง ด้วย OCR

คำอธิบายโปรเจค
โปรเจคนี้เป็นเว็บแอปพลิเคชันสำหรับอ่านข้อมูลจากสติกเกอร์วัคซีนสัตว์เลี้ยง โดยใช้ Optical Character Recognition หรือ OCR ในการดึงข้อมูลต่างๆ ออกมาเป็นข้อความ เช่น ชื่อวัคซีน Serial Number วันผลิต วันหมดอายุ เลขทะเบียน เป็นต้น

ระบบใช้เทคโนโลยี OCR สองตัวร่วมกัน คือ Tesseract OCR และ EasyOCR เพื่อให้ได้ผลลัพธ์ที่ดีและแม่นยำที่สุด โดยจะแบ่งสติกเกอร์ออกเป็น 2 ส่วน คือ ส่วนซ้ายและส่วนขวา แล้วประมวลผลแยกกัน

ฟังก์ชันหลักของระบบ
- อัพโหลดรูปภาพสติกเกอร์วัคซีน
- แบ่งรูปภาพออกเป็น 2 ส่วน ซ้ายและขวา
- ปรับแต่งและเตรียมรูปภาพก่อนส่งเข้า OCR
- ใช้ OCR สามแบบ ได้แก่ Tesseract EasyOCR และ Hybrid
- เปรียบเทียบผลลัพธ์จาก OCR ทั้ง 3 แบบ
- ดึงข้อมูลสำคัญออกมา เช่น ชื่อวัคซีน ชื่อการค้า ผู้ผลิต เลขทะเบียน Serial Number วันผลิต วันหมดอายุ
- แสดงผลลัพธ์เป็นภาษาไทย

โครงสร้างไฟล์ในโปรเจค

โฟลเดอร์หลัก
- app.py ไฟล์หลักของโปรเจค เป็น Flask application
- preprocessing.py โมดูลสำหรับประมวลผลรูปภาพ แบ่งภาพ หมุนภาพ ปรับแต่งก่อนส่ง OCR
- ocr_engines.py โมดูลที่รวม OCR engine ทั้งหมด Tesseract EasyOCR และ Hybrid
- data_extraction.py โมดูลสำหรับดึงข้อมูลจากข้อความที่ได้จาก OCR เช่น ชื่อวัคซีน วันที่ Serial Number
- requirements.txt รายการ Python packages ที่ต้องติดตั้ง
- templates/ โฟลเดอร์เก็บไฟล์ HTML
- static/ โฟลเดอร์เก็บไฟล์สแตติก ถ้ามี
- uploads/ โฟลเดอร์เก็บรูปภาพที่อัพโหลด
- uploads/temp/ โฟลเดอร์เก็บรูปภาพที่ประมวลผลแล้ว

ความต้องการของระบบ
- Python เวอร์ชัน 3.8 ขึ้นไป
- Tesseract OCR ต้องติดตั้งในเครื่อง
- Pip สำหรับติดตั้ง Python packages

ขั้นตอนการติดตั้งและใช้งาน

1. ติดตั้ง Tesseract OCR
สำหรับ Windows
- ดาวน์โหลด Tesseract จาก https://github.com/UB-Mannheim/tesseract/wiki
- ติดตั้งตามขั้นตอน
- เพิ่ม path ของ Tesseract ลงใน System Environment Variables
- ปกติจะอยู่ที่ C:\Program Files\Tesseract-OCR

สำหรับ Mac
ติดตั้งผ่าน Homebrew
brew install tesseract

สำหรับ Linux Ubuntu Debian
sudo apt-get update
sudo apt-get install tesseract-ocr

2. Clone หรือดาวน์โหลดโปรเจค
ถ้าใช้ Git
git clone URL_ของโปรเจค
cd vaccine_ocr_webapp

หรือดาวน์โหลด ZIP แล้ว extract ออกมา

3. สร้าง Virtual Environment แนะนำ
python -m venv venv

เปิดใช้ Virtual Environment
สำหรับ Windows
venv\Scripts\activate

สำหรับ Mac Linux
source venv/bin/activate

4. ติดตั้ง Python packages
pip install -r requirements.txt

หมายเหตุ การติดตั้ง EasyOCR อาจใช้เวลานาน เพราะต้องดาวน์โหลด model ขนาดใหญ่

5. รันโปรแกรม
python app.py

ระบบจะเริ่มทำงานที่ http://localhost:5001

6. เปิดเว็บเบราว์เซอร์
เข้าไปที่ http://localhost:5001

การใช้งาน
- คลิกปุ่ม เลือกไฟล์ หรือ Choose File
- เลือกรูปภาพสติกเกอร์วัคซีน ไฟล์ JPG PNG JPEG เท่านั้น
- คลิก Upload and Process
- รอสักครู่ ระบบจะประมวลผลด้วย OCR ทั้ง 3 แบบ
- ผลลัพธ์จะแสดงทางหน้าจอ พร้อมรูปภาพที่ประมวลผลแล้ว
- เปรียบเทียบผลลัพธ์จาก Tesseract EasyOCR และ Hybrid
- ระบบจะแนะนำว่า OCR แบบไหนให้ผลลัพธ์ดีที่สุด

ข้อมูลที่ระบบดึงออกมาได้
- ชื่อวัคซีน Vaccine Name
- ชื่อการค้า Product Name
- ผู้ผลิต Manufacturer
- เลขทะเบียน Registration Number
- Serial Number
- วันผลิต MFG Date
- วันหมดอายุ EXP Date

โครงสร้างโค้ดหลัก

ไฟล์ app.py
เป็นไฟล์หลักของระบบ Flask Application ที่มี
- API endpoint สำหรับอัพโหลดไฟล์ /api/process
- endpoint สำหรับทดสอบการประมวลผลภาพ /api/test_preprocessing
- การจัดการ CORS
- การบันทึกไฟล์อัพโหลด
- เรียกใช้โมดูลต่างๆ เช่น preprocessing ocr_engines data_extraction

ไฟล์ preprocessing.py
โมดูลสำหรับประมวลผลรูปภาพ ประกอบด้วย
- detect_split_point หาจุดแบ่งระหว่างส่วนซ้ายและขวา
- split_image_left_right แบ่งรูปภาพออกเป็น 2 ส่วน
- rotate_90 หมุนรูปภาพ 90 องศา
- preprocess_left_region ประมวลผลส่วนซ้าย เพิ่มขนาด ทำ sharpening ปรับ contrast
- preprocess_right_region ประมวลผลส่วนขวา ขยายภาพ หมุน กลับสี ทำ bilateral filter CLAHE adaptive threshold
- preprocess_right_region_for_tesseract ประมวลผลส่วนขวาสำหรับ Tesseract โดยเฉพาะ ใช้ความละเอียดสูงกว่า

ไฟล์ ocr_engines.py
โมดูลที่รวม OCR engine ต่างๆ
- ocr_tesseract อ่าน OCR ด้วย Tesseract
- ocr_easyocr อ่าน OCR ด้วย EasyOCR
- ocr_hybrid ใช้ทั้ง Tesseract สำหรับส่วนซ้าย และ EasyOCR สำหรับส่วนขวา
- ocr_tesseract_only ใช้ Tesseract เท่านั้นทั้ง 2 ส่วน
- ocr_easyocr_only ใช้ EasyOCR เท่านั้นทั้ง 2 ส่วน

ไฟล์ data_extraction.py
โมดูลสำหรับดึงข้อมูลจากข้อความ OCR ประกอบด้วย
- normalize_ocr_text แก้ไขข้อความที่ OCR ผิดบ่อย เช่น O เป็น 0 หรือ MFG สะกดผิด
- extract_vaccine_name ดึงชื่อวัคซีน
- extract_product_name ดึงชื่อการค้า เช่น DEFENSOR FELOCELL
- extract_manufacturer ดึงชื่อผู้ผลิต
- extract_registration_number ดึงเลขทะเบียน
- extract_serial_number ดึง Serial Number
- extract_mfg_date ดึงวันผลิต
- extract_exp_date ดึงวันหมดอายุ
- format_date จัดรูปแบบวันที่ให้เป็นมาตรฐาน
- validate_vaccine_data ตรวจสอบว่าข้อมูลครบหรือไม่

ปัญหาที่อาจพบและวิธีแก้ไข

ปัญหา Tesseract ไม่พบ
- ตรวจสอบว่าติดตั้ง Tesseract แล้ว
- เพิ่ม path ของ Tesseract ใน System Environment Variables
- ลองรัน tesseract --version ใน command line ดูว่าใช้งานได้

ปัญหา EasyOCR ติดตั้งไม่สำเร็จ
- ต้องการ PyTorch ติดตั้งก่อน
- อาจต้องใช้ Python เวอร์ชันที่ใหม่กว่า
- ถ้า GPU ไม่มี ให้ใช้ cpu เท่านั้นก็ได้ ระบบตั้งค่าไว้ gpu=False อยู่แล้ว

ปัญหา OCR อ่านผิด
- ลองถ่ายรูปให้ชัดขึ้น
- ตรวจสอบแสงไม่สะท้อน
- ให้สติกเกอร์อยู่ในกรอบตรง ไม่เอียง
- ลองปรับพารามิเตอร์การประมวลผลภาพ

ปัญหา Port 5001 ถูกใช้แล้ว
- เปลี่ยน port ในไฟล์ app.py บรรทัดสุดท้าย
- app.run(debug=True, host='0.0.0.0', port=5001)
- เปลี่ยน 5001 เป็นเลขอื่น เช่น 5002 5003

การพัฒนาเพิ่มเติม
ถ้าต้องการปรับปรุงหรือเพิ่มฟังก์ชัน สามารถทำได้ ดังนี้

1. ปรับแต่งการประมวลผลภาพ
แก้ไขที่ไฟล์ preprocessing.py ปรับพารามิเตอร์ต่างๆ เช่น scale alpha beta blockSize เพื่อให้อ่าน OCR ได้ดีขึ้น

2. เพิ่มการดึงข้อมูลอื่นๆ
แก้ไขที่ไฟล์ data_extraction.py เพิ่มฟังก์ชันดึงข้อมูลใหม่ๆ หรือปรับ regex pattern

3. เพิ่ม UI
แก้ไขที่ templates/index.html เพิ่ม CSS JavaScript เพื่อให้หน้าตาสวยขึ้น

4. เพิ่มการบันทึกข้อมูล
เพิ่มการบันทึกผลลัพธ์ลงฐานข้อมูล เช่น SQLite MySQL หรือ export เป็น Excel CSV

5. รองรับสติกเกอร์หลายแบบ
ปรับปรุงระบบให้รองรับสติกเกอร์วัคซีนหลายยี่ห้อ หลายรูปแบบ

ข้อแนะนำ
- ถ่ายรูปสติกเกอร์ให้ชัด แสงเพียงพอ
- หลีกเลี่ยงแสงสะท้อน
- พยายามให้สติกเกอร์อยู่ในแนวตรง ไม่เอียงมาก
- ถ้ารูปภาพมีขนาดใหญ่เกินไป ระบบอาจประมวลผลช้า
- ขนาดไฟล์ไม่เกิน 5 MB

