# Project Scada Monitoring Line

โปรเจกต์สำหรับดึงข้อมูลจาก Kepware (OPC UA) มาเก็บใน Database เพื่อนำไปใช้งานต่อใน Django หรือระบบ Monitoring อื่นๆ

## โครงสร้างโปรเจกต์
- `collector/`: ไฟล์หลักสำหรับการดึงข้อมูล
    - `main.py`: โปรแกรมดึงข้อมูล (Collector)
    - `config.py`: ตั้งค่า IP และ Database
    - `setup_db.py`: ใช้เตรียม Database (สำหรับทดสอบ)
- `database/`: ไฟล์ SQL Schema

## วิธีเริ่มต้นใช้งาน (Quick Start)

1. **ติดตั้ง Library ที่จำเป็น:**
   ```bash
   pip install -r requirements.txt
   ```

2. **เตรียม Database:**
   (หากใช้ SQLite เพื่อทดสอบให้รันคำสั่งนี้)
   ```bash
   cd collector
   python setup_db.py
   ```

3. **แก้ไข Tag ที่ต้องการ Monitor:**
   - เปิดไฟล์ `scada_data.db` (หรือ PostgreSQL) แล้วเพิ่มรายชื่อ Tag ที่ต้องการลงในตาราง `tag_config`
   - ใส่ชื่อ Tag และ Address ให้ตรงกับใน Kepware (เช่น `ns=2;s=Line1.Machine1.Status`)

4. **เริ่มรันโปรแกรม:**
   ```bash
   python main.py
   ```

## การปรับจูน (Adjustment)
- **เพิ่ม Tag:** ไม่ต้องหยุดโปรแกรม แค่เพิ่มแถวใหม่ในตาราง `tag_config` โปรแกรมจะดึงข้อมูลมาเองในรอบถัดไป
- **ประสิทธิภาพ:** โปรแกรมใช้ Async IO และ Batch Insert เพื่อรองรับ 1,000+ Tags ได้อย่างสบาย
- **PostgreSQL:** หากต้องการใช้งานจริงกับข้อมูลจำนวนมาก ให้เปลี่ยน `DB_TYPE = "postgres"` ใน `config.py`
