# เอกสารเทคนิคระบบ MCOT Rental Platform (ปรับปรุงล่าสุด)

เวอร์ชัน: 3.0  
อัปเดตล่าสุด: 12 มีนาคม 2569

---

## 1) ภาพรวมระบบ

MCOT Rental Platform เป็นระบบจองอุปกรณ์ สตูดิโอ และแพ็กเกจ สำหรับทั้งลูกค้าภายนอกและทีมงานภายใน โดย flow หลักคือ:

1. เลือกรายการในตะกร้า
2. ตรวจสอบช่วงวันและความพร้อมใช้งาน
3. สร้างการจอง
4. อัปโหลดหลักฐานการชำระเงิน
5. ให้ทีมงานอนุมัติและดำเนินงานต่อ

จุดสำคัญของเวอร์ชันปัจจุบัน:

- ปรับเสถียรภาพการสร้าง booking เมื่อ cart มีข้อมูล stale/missing id ให้ตอบกลับเป็น validation conflict แทนการเกิด 500
- ปรับกติกา package ให้จองแบบ standalone ได้ (ไม่บังคับต้องมี PackageItem เสมอ)
- ปรับธีมและ responsive โดยเน้น mobile-first ในหน้า auth และหน้าสำคัญฝั่งลูกค้า

---

## 2) เทคโนโลยีหลัก

- Backend: Django 4.2.x
- Language: Python 3.9+
- Database (dev): SQLite
- Frontend: Django Templates + Tailwind utility classes
- Admin: Django Admin (มีการปรับแต่งเพิ่มเติม)
- เอกสาร/รายงาน: Browser print + PDF endpoints

หมายเหตุ: รายการ dependency ให้ยึดตาม requirements.txt ใน repository เป็นหลัก

---

## 3) โครงสร้างโปรเจกต์ที่ใช้งานจริง

โฟลเดอร์หลักที่ต้องรู้:

- config/: ค่า settings, urls, asgi/wsgi และ admin site customization
- apps/store/: business domain หลักของระบบ
- templates/: หน้าเว็บทั้งหมด (customer/auth/staff/admin override)
- static/: css, fonts, images
- media/: ไฟล์อัปโหลด เช่น สลิปชำระเงิน

ส่วนสำคัญใน apps/store/:

- models.py: โมเดลธุรกิจหลัก
- urls.py: routing ของแอป
- views/: แยกเป็นโมดูลตามโดเมน (booking, products, pages, staff, user, notification)
- services/: service layer สำหรับ business logic
- management/commands/: custom command เช่น import ratecard และงาน background เชิง maintenance

---

## 4) โดเมนข้อมูลหลัก

โมเดลหลักของระบบ:

- Catalog/Resource: Product, Equipment, Studio, Package, PackageItem
- People/Role: Staff, StaffPosition, Profile
- Booking: Booking, BookingItem, BookingStudio, BookingStaff, BookingPackage
- Config/Promotion: ProductCategory, PromotionCode

สถานะการจองและการเงินถูกเก็บแยกกัน เพื่อรองรับ flow อนุมัติและการเงินที่ต่างจังหวะกัน

---

## 5) Service Layer

Service ที่ใช้งานในปัจจุบัน:

- AvailabilityService
  - ตรวจสอบความพร้อมใช้งานของสินค้าตามช่วงวันและปริมาณ
  - รองรับการตรวจทั้งระดับ item และ cart
  - เวอร์ชันล่าสุดรองรับ package แบบ standalone

- BookingService
  - แปลง payload จาก cart เป็น booking records
  - ป้องกัน crash จากข้อมูล cart ที่ไม่ตรงกับฐานข้อมูล
  - ส่งผลลัพธ์เชิง validation ที่ UI จัดการต่อได้

- PricingService
  - คำนวณยอดเช่า ส่วนลด โค้ดโปร และยอดมัดจำ

- NotificationService
  - จัดการการแจ้งเตือนฝั่งผู้ใช้และทีมงาน

- DocumentService
  - เตรียมข้อมูลออกเอกสารใบจอง/ใบเสนอราคา

- DashboardService
  - รวมข้อมูลสรุปสำหรับ staff dashboard และรายงาน

---

## 6) URL และ Endpoint สำคัญ

เส้นทางที่ใช้งานบ่อย:

- /cart/
- /cart/review/
- /api/check-availability/
- /api/check-cart/
- /api/booking/create/
- /api/booking/<id>/upload-slip/
- /api/staff/booking/<id>/action/
- /staff/booking/<id>/summary/
- /staff/analytics/

หมายเหตุ: รายชื่อ URL แบบครบถ้วนให้ดูจาก apps/store/urls.py และ config/urls.py

---

## 7) Frontend และ UX

แนวทางหน้าเว็บปัจจุบัน:

- รองรับ dark theme ในหน้า auth และหน้าลูกค้าหลัก
- mobile-first เป็นค่าเริ่มต้นในการปรับ layout ใหม่
- แก้จุดชน/ล้นในหน้าที่มี sticky bar, breadcrumb และ action bar ด้านล่าง
- ใช้ safe-area aware spacing บนอุปกรณ์มือถือที่มี gesture area

หน้าเทมเพลตที่ได้รับการปรับล่าสุดเน้นที่:

- auth flow ทั้ง account/registration
- หน้า home
- หน้า catalog และหน้า detail ของ product/package/studio

---

## 8) การทดสอบ

คำสั่งตรวจสุขภาพระบบที่แนะนำ:

```bash
python3 manage.py check
python3 manage.py test apps.store.tests_auth
python3 manage.py test apps.store.tests
```

แนวทาง test ที่ควรครอบคลุม:

- booking creation success path
- stale/missing ids ใน cart ต้องไม่ทำให้ระบบ 500
- package booking แบบไม่มี PackageItem ต้องผ่านตาม business rule ปัจจุบัน
- auth pages และ flow สำคัญต้อง render ได้ทั้ง desktop/mobile

---

## 9) Deployment และ Configuration

หลักการขั้นต่ำก่อน deploy:

1. ปิด DEBUG
2. ตั้งค่า ALLOWED_HOSTS ตามโดเมนจริง
3. ตั้ง SECRET_KEY ผ่าน environment variable
4. จัดการ static/media ให้เหมาะกับ production
5. ย้ายฐานข้อมูลจาก SQLite ไป PostgreSQL/MySQL ตาม environment จริง

สำหรับทดสอบจากภายนอกองค์กร อาจใช้ tunnel เช่น ngrok/serveo โดยต้องกำหนด CSRF_TRUSTED_ORIGINS ให้ตรงโดเมนที่ใช้งาน

---

## 10) Repository Hygiene

แนวทางที่ใช้อยู่ในโปรเจกต์:

- ไม่ track ไฟล์ฐานข้อมูล local และไฟล์ local tooling
- ไม่เก็บไฟล์ build artifacts หรือ dependencies ที่ติดตั้งในเครื่อง
- ทำความสะอาด tracked-but-ignored files ด้วยการ untrack จาก git index

ให้ตรวจ .gitignore ร่วมกับสถานะ git ทุกครั้งก่อน commit

---

## 11) Known Decisions (อัปเดตตามโค้ดปัจจุบัน)

- การสร้าง booking จาก cart ที่มีข้อมูลผิด/เก่า ต้องตอบแบบ validation conflict แทน error ภายในเซิร์ฟเวอร์
- Package ถือเป็นรายการที่จองได้เอง (standalone booking) ไม่บังคับว่าต้องมี PackageItem
- Mobile-first และความอ่านง่ายบนหน้าจอเล็ก เป็นเกณฑ์หลักของการปรับ UI รอบล่าสุด

---

## 12) ภาคผนวก: ไฟล์อ้างอิงที่ควรอ่านต่อ

- AI_CONTEXT.md: สถานะงานและข้อควรทราบล่าสุดสำหรับผู้พัฒนา
- USER_MANUAL.md: คู่มือใช้งานเชิงธุรกิจ/ผู้ใช้ระบบ
- apps/store/services/: รายละเอียด business logic เชิงโค้ด
- templates/: พฤติกรรมจริงของหน้าเว็บฝั่งผู้ใช้งาน

เอกสารฉบับนี้ตั้งใจให้เป็นแหล่งอ้างอิงเชิงปฏิบัติสำหรับทีมพัฒนา หากมีการเปลี่ยน business rule หรือ flow การจอง ให้ปรับเอกสารนี้พร้อมกับการเปลี่ยนโค้ดทุกครั้ง

---

## 13) Runbook (Deploy / Rollback / Incident)

ส่วนนี้เป็นขั้นตอนปฏิบัติการแบบสั้นสำหรับทีมที่ดูแล production

### 13.1 Pre-Deploy Checklist

1. ตรวจ branch และ commit ที่จะขึ้นระบบ
2. รันตรวจพื้นฐานในเครื่องพัฒนา

```bash
python3 manage.py check
python3 manage.py test apps.store.tests_cancellation apps.store.tests_state_transitions
```

3. ตรวจว่าไฟล์ที่ไม่ควร track ไม่ติดขึ้น git status
4. ยืนยันค่า environment สำคัญในเซิร์ฟเวอร์ โดยเฉพาะ `DATABASE_URL`, `SECRET_KEY`, `ALLOWED_HOSTS`

### 13.2 Post-Deploy Smoke Test

หลัง deploy ให้ทดสอบทันทีด้วยสคริปต์

```bash
BASE_URL=https://mcotequipmentservices.mcot.net ./scripts/smoke_test.sh
```

เกณฑ์ผ่านเบื้องต้น:
1. หน้า Home, Catalog, Login ตอบกลับ 200/301/302
2. หน้า `my-bookings` redirect ไป login ได้ปกติเมื่อยังไม่ล็อกอิน

### 13.3 Rollback แบบเร็ว

กรณี deploy แล้วมีปัญหา ให้ rollback ด้วยวิธีที่คาดเดาได้

```bash
git log --oneline -n 5
git checkout <last_known_good_commit>
python3 manage.py migrate --noinput
python3 manage.py collectstatic --noinput
sudo systemctl restart gunicorn
```

จากนั้นรัน smoke test ซ้ำอีกรอบ

### 13.4 Monitoring ขั้นต่ำบน VPS

มีสคริปต์ตรวจสุขภาพระบบ

```bash
./scripts/health_check_vps.sh
```

สิ่งที่ตรวจ:
1. service (`gunicorn`) active
2. HTTP ตอบกลับจากโดเมนหลัก
3. disk usage ไม่เกิน threshold

ตัวอย่างตั้ง cron ทุก 5 นาที:

```bash
*/5 * * * * /home/ubuntu/MCOT_Rental_Platform/scripts/health_check_vps.sh >> /var/log/mcot-health.log 2>&1
```

### 13.5 Known Ops Pitfall

1. หลีกเลี่ยงใช้ key ซ้ำซ้อน (`DATABASE_URL` กับ `DATABASES_URL`) ใน production
2. ให้ใช้ `DATABASE_URL` เพียงตัวเดียวเป็นมาตรฐาน
3. หากเจอ working tree สกปรกระหว่าง deploy ให้ stash ก่อน pull แล้ว cleanup หลัง deploy ทุกครั้ง
