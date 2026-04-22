# 🚀 Project SCADA Monitoring Line

ระบบดึงข้อมูลจาก Kepware (OPC UA) มาพักไว้ใน Database เพื่อรองรับการทำ Web Monitoring และจัดการ Tag จำนวนมากได้ง่าย

---

## 🛠️ ขั้นตอนการติดตั้ง (Setup)

### 1. ติดตั้ง Library ที่จำเป็น
เปิด Terminal ในโฟลเดอร์โปรเจกต์แล้วรันคำสั่ง:
```bash
pip install -r requirements.txt
```

### 2. ตั้งค่าไฟล์คอนฟิก (.env)
แก้ไขไฟล์ `.env` ที่อยู่โฟลเดอร์หลัก:
* `OPC_SERVER_URL`: IP ของ Kepware Server
* `OPC_USER` / `OPC_PASSWORD`: ใส่ถ้ามีการตั้งรหัสผ่านที่ Kepware
* `POLLING_INTERVAL`: ความถี่ในการดึงข้อมูล (วินาที)

### 3. เตรียม Database (รันครั้งแรกเท่านั้น)
```bash
cd collector
python3 setup_db.py
```

---

## 📑 การจัดการ Tag (ง่ายที่สุดผ่าน Excel/CSV)

ไม่ต้องเปิด Database เอง! ให้จัดการผ่านไฟล์ CSV ในโฟลเดอร์ `Tag/` แทน:

1. **แก้ไขไฟล์ CSV**: เปิดไฟล์ `collector/Tag/sample_tags.csv` ด้วย Excel เพื่อใส่รายชื่อ Tag (หรือสร้างไฟล์ .csv ใหม่ในโฟลเดอร์นั้น)
2. **คอลัมน์ที่ต้องมี**: `machine_name`, `tag_name`, `opc_address`, `deadband`, `description`
3. **สั่ง Update ข้อมูลเข้า Database**:
```bash
python3 import_csv_tags.py
```
*(คุณสามารถรันคำสั่งนี้ได้ตลอดเมื่อมีการเพิ่มหรือแก้ไขรายชื่อ Tag ใน CSV)*

---

## 🏃 การเริ่มรันระบบ (Running)

เริ่มการดึงข้อมูลจาก Kepware ลง Database:
```bash
python3 main.py
```

### 💡 ข้อแนะนำการใช้งานจริง
* **การเพิ่ม Tag**: แค่แก้ไขไฟล์ CSV แล้วรัน `import_csv_tags.py` ระบบจะอัปเดต Tag ใหม่ให้ทันทีโดยไม่ต้องหยุด `main.py`
* **OPC UA Trust**: อย่าลืมไปกด **Trust** ให้กับ Client ในโปรแกรม **OPC UA Configuration** ของ Kepware ในการรันครั้งแรก

---

## 📂 โครงสร้างโปรเจกต์
* `collector/`: โปรแกรมดึงข้อมูลหลัก
* `web/`: ระบบหน้าเว็บ Django (Dashboard & Admin)
* `database/`: ที่เก็บไฟล์ Database (`scada_data.db`)
* `collector/Tag/`: โฟลเดอร์เก็บไฟล์ CSV สำหรับตั้งค่า Tag
* `.env`: ไฟล์เก็บการตั้งค่าการเชื่อมต่อทั้งหมด

---

## 🌐 ระบบหน้าเว็บ (Web Dashboard & Admin)

เรามีระบบหน้าเว็บสำหรับดูข้อมูลแบบ Real-time และจัดการ Tag:

### 1. วิธีเริ่มรันหน้าเว็บ
```bash
cd web
./run_web.sh
```
จากนั้นเปิดเบราว์เซอร์ไปที่: `http://localhost:8000`

### 2. การจัดการ Tag ผ่านหน้าเว็บ (Admin)
คุณสามารถจัดการ Machine และ Tag ได้ง่ายๆ ผ่านหน้า Admin:
* **URL**: `http://localhost:8000/admin`
* **User**: `admin`
* **Password**: `admin123`

### 3. Dashboard หน้าตาพรีเมียม
หน้าแรกจะแสดงสถานะของทุกเครื่องจักร (Machine) และค่าของ Tag แบบ Real-time พร้อมไฟสถานะ Online/Offline โดยจะทำการรีเฟรชข้อมูลเองอัตโนมัติทุก 5 วินาที
