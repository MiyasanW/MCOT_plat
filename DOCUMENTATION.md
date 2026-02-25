# 📖 เอกสารเทคนิคระบบ MCOT Rental Platform

**เวอร์ชัน:** 2.0  
**วันที่จัดทำ:** 25 กุมภาพันธ์ 2569  
**จัดทำโดย:** ทีมพัฒนาระบบ MCOT Rental Platform

---

## สารบัญ

1. [ภาพรวมโครงการ](#1-ภาพรวมโครงการ)
2. [สถาปัตยกรรมระบบ](#2-สถาปัตยกรรมระบบ)
3. [แบบจำลองข้อมูล (Data Models)](#3-แบบจำลองข้อมูล)
4. [หน้าจอผู้ดูแลระบบ (Admin Panel)](#4-หน้าจอผู้ดูแลระบบ)
5. [ส่วนแสดงผลหน้าเว็บ (Views)](#5-ส่วนแสดงผลหน้าเว็บ)
6. [ชั้นตรรกะทางธุรกิจ (Service Layer)](#6-ชั้นตรรกะทางธุรกิจ)
7. [เส้นทาง URL (API & Routes)](#7-เส้นทาง-url)
8. [เทมเพลตหน้าเว็บ (Templates)](#8-เทมเพลตหน้าเว็บ)
9. [เครื่องมือเสริมและคำสั่ง (Utilities)](#9-เครื่องมือเสริมและคำสั่ง)
10. [การทดสอบระบบ (Testing)](#10-การทดสอบระบบ)
11. [การออกแบบหน้าตา (Styling & Design)](#11-การออกแบบหน้าตา)
12. [การตั้งค่าและนำขึ้นใช้งาน (Configuration & Deployment)](#12-การตั้งค่าและนำขึ้นใช้งาน)

---

## 1. ภาพรวมโครงการ

### วัตถุประสงค์

MCOT Rental Platform เป็น **ระบบจัดการการเช่าอุปกรณ์โปรดักชันและสตูดิโอ** ของ บมจ. อสมท สำหรับลูกค้าภายนอกและทีมงานภายใน โดยครอบคลุมตั้งแต่การเลือกอุปกรณ์ → การจอง → ชำระเงิน → เบิกจ่ายอุปกรณ์ → คืนของ → ออกเอกสาร

### คุณสมบัติหลัก

- 🛒 **ระบบตะกร้าสินค้า (Cart):** ลูกค้าเลือกอุปกรณ์ สตูดิโอ แพ็คเกจ แล้วจองได้ในรอบเดียว
- 📅 **ระบบตรวจสอบคิวว่าง (Availability):** เช็คจำนวนอุปกรณ์คงเหลือและการจองซ้อนแบบ Real-time (ป้องกัน Overbooking แบบ Concurrency)
- 💰 **ระบบคำนวณราคาอัตโนมัติ:** คิดราคาตามวัน × จำนวนชิ้น, รองรับส่วนลดพาร์ทเนอร์ โค้ดโปรโมชั่น และคิดค่าปรับส่งคืนล่าช้า
- 📄 **ระบบออกเอกสาร:** ใบเสนอราคาและใบจ่ายงาน (Work Order) รองรับการพิมพ์ผ่านหน้าเบราว์เซอร์ (Browser Print)
- 🔔 **ระบบแจ้งเตือน:** แจ้งเตือนบนเว็บไซต์ (In-App) + อีเมลอัตโนมัติ
- 🔐 **ระบบสิทธิ์ตามบทบาท (RBAC):** แบ่ง Superuser, Web Admin, Staff, ลูกค้า
- 📊 **หน้า Dashboard พนักงาน (Staff Summary & Analytics):** สถิติรายได้ จำนวนจอง สถานะอุปกรณ์ พร้อม Quick Action ลดการพึ่งพาตัว Admin หลัก
- 🚀 **UI สุดล้ำ (Premium Glassmorphism):** หน้า UI ฝั่งผู้ใช้ถูกออกแบบให้ทันสมัย หรูหรา ระดับองค์กรสื่อ (Cinematic Dark Mode)

### เทคโนโลยีที่ใช้

| ส่วน                      | เทคโนโลยี             | เวอร์ชัน      |
| ------------------------- | --------------------- | ------------- |
| **Backend Framework**     | Django                | 4.2.27        |
| **ภาษาโปรแกรม**           | Python                | 3.9+          |
| **ฐานข้อมูล**             | SQLite                | (Development) |
| **Frontend CSS**          | Tailwind CSS          | CDN           |
| **Admin Theme**           | Django Unfold         | ล่าสุด        |
| **กราฟสถิติ**             | Chart.js              | 4.x           |
| **Rich Text Editor**      | Summernote            | 0.8.20        |
| **ระบบ Import/Export**    | django-import-export  | 3.3.6         |
| **ประวัติการเปลี่ยนแปลง** | django-simple-history | —             |
| **ตัวกรองข้อมูล**         | django-filter         | 23.5          |

---

## 2. สถาปัตยกรรมระบบ

### โครงสร้างไดเรกทอรีหลัก

```
MCOT_Rental_Platform/
├── config/                    # ⚙️ การตั้งค่าระบบ
│   ├── settings.py           # ค่าตั้งทั้งหมดของ Django (เพิ่ม CSRF_TRUSTED_ORIGINS สำหรับ ngrok/serveo)
│   ├── urls.py               # เส้นทาง URL หลัก
│   ├── admin_site.py         # ปรับแต่งหน้า Admin Sidebar (ใช้ Unfold)
│   └── dashboard.py          # ข้อมูลสถิติหน้า Dashboard
│
├── apps/store/               # 📦 แอปพลิเคชันหลัก
│   ├── models.py             # แบบจำลองข้อมูล (20+ Models)
│   ├── admin.py              # การตั้งค่าหน้า Admin ด้วย Unfold (600+ บรรทัด)
│   ├── forms.py              # ฟอร์มสมัครสมาชิก
│   ├── urls.py               # เส้นทาง URL ของแอป (40+ Routes)
│   ├── validators.py         # Validator รหัสผ่านภาษาไทย
│   ├── views/                # ส่วนแสดงผล (7 Modules)
│   │   ├── pages.py          # หน้าสาธารณะ
│   │   ├── products.py       # แคตตาล็อกสินค้า
│   │   ├── booking.py        # ระบบจอง + API
│   │   ├── user.py           # สมัครสมาชิก + Dashboard ลูกค้า
│   │   ├── staff.py          # เครื่องมือเจ้าหน้าที่ (Staff Summary, Analytics) + PDF
│   │   ├── calendar.py       # ปฏิทินการจอง
│   │   └── notification.py   # ระบบแจ้งเตือน API
│   ├── services/             # ชั้นตรรกะทางธุรกิจ (6 Services)
│   │   ├── availability.py   # ตรวจสอบสินค้าว่าง
│   │   ├── booking_service.py# จัดการการจอง
│   │   ├── pricing_service.py# คำนวณราคา
│   │   ├── notification_service.py # แจ้งเตือน
│   │   ├── document_service.py     # สร้างข้อมูลออกเอกสาร
│   │   └── dashboard_service.py    # สถิติ Dashboard
│   ├── utils/                # เครื่องมือเสริม
│   │   └── ratelimit.py      # ป้องกันการ Spam Request
│   └── management/commands/  # คำสั่ง CLI
│       ├── cancel_expired_bookings.py
│       └── import_ratecard.py
│
├── templates/                # 🎨 เทมเพลต HTML (40+ ไฟล์) รวมถึง Staff Quick Summary
├── static/css/               # 🖌️ ไฟล์ CSS
└── requirements.txt          # 📋 รายการแพ็คเกจ
```

---

## 3. แบบจำลองข้อมูล

### 3.1 กลุ่มตั้งค่าระบบ (Configuration)

| Model               | คำอธิบาย                                  | ฟิลด์สำคัญ                                                                           |
| ------------------- | ----------------------------------------- | ------------------------------------------------------------------------------------ |
| **ProductCategory** | หมวดหมู่สินค้า (กล้อง, เลนส์, ไฟ, รถ OB)  | `name`, `slug`                                                                       |
| **StaffPosition**   | ตำแหน่งพนักงาน (ช่างภาพ, ครีเอทีฟ, คนขับ) | `name`, `base_daily_rate`                                                            |
| **PromotionCode**   | โค้ดโปรโมชั่น / ส่วนลด                    | `code`, `discount_percent`, `discount_amount`, `valid_from`, `valid_to`, `is_active` |

### 3.2 กลุ่มข้อมูลผู้ใช้ (User)

| Model       | คำอธิบาย                                    | ฟิลด์สำคัญ                                        |
| ----------- | ------------------------------------------- | ------------------------------------------------- |
| **Profile** | ข้อมูลเพิ่มเติมผู้ใช้ (ขยายจาก Django User) | `phone`, `is_partner`, `partner_discount_percent` |

ระบบสร้าง Profile ให้อัตโนมัติทุกครั้งที่มีการสร้าง User ใหม่ ผ่าน Django Signal (`post_save`)

### 3.3 กลุ่มทรัพยากร (Resources)

| Model                 | คำอธิบาย                           | ฟิลด์สำคัญ                                                                                       |
| --------------------- | ---------------------------------- | ------------------------------------------------------------------------------------------------ |
| **Product**           | สินค้า/อุปกรณ์หลัก                 | `name`, `price`, `quantity`, `category`, `image`, `is_active`, `is_featured`, `late_fee_per_day` |
| **Equipment**         | อุปกรณ์รายชิ้น (มี Serial Number)  | `product`, `serial_number`, `inventory_number`, `asset_tag`, `status`                            |
| **Studio**            | สตูดิโอ                            | `name`, `description`, `daily_rate`, `turnaround_time`                                           |
| **Package**           | แพ็คเกจรวมสินค้า                   | `name`, `price`, `image`, `is_highlight`, `is_active`, `items` (M2M)                             |
| **PackageItem**       | รายการสินค้าภายในแพ็คเกจ           | `package`, `product`, `quantity`                                                                 |
| **Staff**             | พนักงาน/ทีมงาน                     | `name`, `position`, `daily_rate`, `phone`, `is_active`                                           |
| **ProductionVehicle** | ยานพาหนะ (Proxy Model จาก Product) | สืบทอด Product ทุกฟิลด์                                                                          |

### 3.4 กลุ่มการจอง (Booking)

| Model              | คำอธิบาย           | ฟิลด์สำคัญ                                                                                                                              |
| ------------------ | ------------------ | --------------------------------------------------------------------------------------------------------------------------------------- |
| **Booking**        | การจองหลัก         | `customer_name`, `start_time`, `end_time`, `status`, `payment_status`, `payment_slip`, `deposit_amount`, `internal_notes`, `expires_at` |
| **BookingItem**    | รายการสินค้าที่จอง | `booking`, `product`, `quantity`, `price_at_booking`, `equipment`, `status`                                                             |
| **BookingStudio**  | สตูดิโอที่จอง      | `booking`, `studio`, `price_at_booking`                                                                                                 |
| **BookingStaff**   | ทีมงานที่จอง       | `booking`, `staff`, `daily_rate_at_booking`                                                                                             |
| **BookingPackage** | แพ็คเกจที่จอง      | `booking`, `package`, `quantity`, `price_at_booking`                                                                                    |

### สถานะการจอง (Booking Status Flow)

```
📝 Draft (รอตรวจสอบจาก Staff กำหนดมัดจำ)
 │
 ├──→ ⏳ Pending (รอชำระเงิน/รออนุมัติ)
 │     │
 │     ├──→ ✅ Approved (อนุมัติแล้ว)
 │     │     │
 │     │     └──→ ▶ Active (กำลังใช้งาน)
 │     │           │
 │     │           ├──→ ✔ Completed (คืนของครบ)
 │     │           │
 │     │           └──→ ⚠️ Overdue (เกินกำหนด/มีค่าปรับ)
 │     │                 │
 │     │                 └──→ ✔ Completed (คืนของครบ เคลียร์ค่าปรับแล้ว)
 │     │
 │     └──→ ❌ Cancelled (ยกเลิก)
 │
 └──→ ❌ Cancelled (ยกเลิก หรือหมดอายุ)
```

### สถานะการชำระเงิน (Payment Status)

| สถานะ      | คำอธิบาย                    |
| ---------- | --------------------------- |
| `unpaid`   | ยังไม่จ่าย                  |
| `pending`  | รอตรวจสอบสลิป (แนบสลิปแล้ว) |
| `paid`     | จ่ายแล้ว                    |
| `refunded` | คืนเงินแล้ว                 |

---

## 4. หน้าจอผู้ดูแลระบบ

เราแบ่งหน้าสำหรับทีมงานออกเป็น 2 ชั้น เพื่อลดความซับซ้อน:

1. **Django Admin (Unfold Theme):** สำหรับตั้งค่าระดับฐานข้อมูล เช่น เพิ่มสินค้า จัดการผู้ใช้งาน
2. **Staff Quick Summary & Analytics (Frontend):** หน้ารวมศูนย์สำหรับเข้าจัดการออเดอร์ (Approve, Confirm Payment) ภายในไม่กี่คลิก และหน้าสถิติ Analytics เชิงลึก ซึ่งสามารถเข้าถึงได้ผ่าน URL ฝั่ง Frontend โดยตรง

### 4.1 ระบบสิทธิ์ตามบทบาท (Role-Based Access Control)

| บทบาท                 | สิทธิ์การเข้าถึง                                                 |
| --------------------- | ---------------------------------------------------------------- |
| **Superuser**         | เข้าถึงทุกส่วน (Django Admin ระดับสูงสุด)                        |
| **Web Admin**         | จัดการการจอง, อนุมัติ/ยกเลิก, ยืนยันการชำระเงิน, จัดการแคตตาล็อก |
| **Staff**             | ดูรายการจอง, เปลี่ยนสถานะผ่านหน้าระบบ Quick Summary              |
| **ลูกค้า (Customer)** | ไม่สามารถเข้า Admin ได้ — ใช้เว็บไซต์หน้าบ้านเท่านั้น            |

### 4.2 ระบบ Staff Quick Summary (Frontend Dashboard)

หน้าเว็บออกแบบให้เป็น **Glassmorphic Interactive Dashboard** โดยที่พนักงานกดดูจากการแจ้งเตือนแล้วกระโดดมายังหน้านี้:

- ตรวจสอบยอดรวม และรายละเอียดออเดอร์ทั้งหมด
- กดปุ่ม Action เพื่อเปลี่ยนสถานะออเดอร์ทันที (Request Payment, Confirm Payment, Active, Completed, Cancel)
- ดูภาพตัวอย่างสลิปโอนเงินได้เลย
- สั่งพิมพ์ "ใบจ่ายงาน" (Equipment Sheet) และ "ใบเสนอราคา" (Quotation) ได้ทันที

### 4.3 Analytics Dashboard

หน้าวิเคราะห์ข้อมูลออกแบบพิเศษสำหรับทีมงาน MCOT:

- **ยอดขายย้อนหลัง (Revenue Trends):** กราฟเส้นแบบรายเดือน
- **หมวดหมู่ยอดนิยม (Top Categories):** กราฟโดนัท (Doughnut Chart) วัดความต้องการอุปกรณ์
- **รายการเช่าวันนี้:** ติดตามงานเช่าที่ต้อง Action ภายในวันนี้ด่วน

---

## 5. ส่วนแสดงผลหน้าเว็บ

### 5.1 ระบบจอง (Booking API)

| ฟังก์ชัน                      | URL                               | คำอธิบาย                                                     |
| ----------------------------- | --------------------------------- | ------------------------------------------------------------ |
| `cart`                        | `/cart/`                          | หน้าตะกร้าสินค้า — รองรับ Promo Code, เช็คข้ามวัน, มัดจำ 30% |
| `check_availability_api`      | `/api/check-availability/`        | API เช็คจำนวนสินค้าคงเหลือ                                   |
| `check_cart_availability_api` | `/api/check-cart/`                | API เช็คทั้งตะกร้า                                           |
| `create_booking_api`          | `/api/booking/create/`            | API สร้างใบจอง (มี Lock Concurrency + 30s Cooldown)          |
| `upload_slip_api`             | `/api/booking/<id>/upload-slip/`  | API อัปโหลดสลิปโอนเงิน                                       |
| `api_staff_booking_action`    | `/api/staff/booking/<id>/action/` | API Quick Action ของระบบ Staff Dashboard                     |

### 5.2 เครื่องมือเจ้าหน้าที่ (Staff Tools)

| ฟังก์ชัน                   | URL                            | คำอธิบาย                        |
| -------------------------- | ------------------------------ | ------------------------------- |
| `staff_analytics`          | `/staff/analytics/`            | หน้ากราฟสถิติรวมขององค์กร       |
| `staff_booking_summary`    | `/staff/booking/<id>/summary/` | หน้าจัดการการจองเดียวครบจบ      |
| `equipment_history_search` | `/staff/history/`              | ค้นหาประวัติการใช้งานอุปกรณ์    |
| `equipment_history_detail` | `/staff/history/<id>/`         | ประวัติรายชิ้น                  |
| `download_booking_pdf`     | `/api/booking/<id>/pdf/`       | พิมพ์ใบจ่ายงาน (Browser Print)  |
| `download_quotation_pdf`   | `/api/booking/<id>/quotation/` | พิมพ์ใบเสนอราคา (Browser Print) |

---

## 6. ชั้นตรรกะทางธุรกิจ

### 6.1 AvailabilityService — ตรวจสอบสินค้าว่าง

ระบบถูกปรับให้ป้องกัน Race Condition ในระหว่างที่ลูกค้ากด Checkout แบบเสี้ยววินาทีพร้อมกัน โดยจะใช้ `select_for_update()` ในระดับดาต้าเบส

### 6.2 PricingService — คำนวณราคา

เพิ่มระบบโปรโมชั่น (Promotion Codes), ส่วนลดพาร์ทเนอร์อัตโนมัติ (Partner Discount) และ ระบบจัดเก็บมัดจำ 30% (Deposit) ตามกฎหมายบริษัท

### 6.3 NotificationService — ระบบแจ้งเตือน

การแจ้งเตือนทั้งหมดในระบบถูกย้ายไปชี้ที่หน้า `Staff Quick Summary` เพื่อให้พนักงานจัดการปัญหาเฉพาะหน้าได้ทันที ไม่ต้องงมในหลังบ้าน ดาต้าเบส Django Admin และระบบมี Polling เช็คอัปเดตแจ้งเตือนทุก 60 วินาที

---

## 7. การออกแบบหน้าตา (Styling & Design)

- **Frontend Theme:** High-End Cinematic Dark Theme (#1A1A1A และ Gradients)
- **Glassmorphism:** ใช้ในหน้า Catalog, Studio Details, Cart, Staff Summary ทำให้กลมกลืน ดูมีความลึก ทันสมัย
- **Django Admin (Unfold Theme):**
  - ติดตั้ง `unfold` framework เพื่อครอบทับ Django Admin แบบดั้งเดิม
  - รองรับ Dark Mode อัตโนมัติในระดับ Admin
  - เมนูด้านซ้ายจัดหมวดหมู่แยกตาม Business Logic (Bookings, Resources, Configurations)
- **การแปลภาษา (Localization):**
  - หน้าสตูดิโอ อุปกรณ์ การแจ้งเตือนต่างๆ ถูกบังคับแปลเป็นภาษาไทย 100% ผ่านฟังก์ชันและเทมเพลต

---

## 8. การทดสอบและนำขึ้นใช้งาน (Deployment & Webhook Testing)

### 8.1 การตั้งค่า ngrok และ Serveo เพื่อทดสอบระบบจากภายนอก

ในการเปิดทดสอบผ่านมือถือหรือให้ทีมงานตรวจ (แชร์ URL ภายนอก ทะลุกำแพง Localhost):
ไฟล์ `config/settings.py` ติดตั้ง `CSRF_TRUSTED_ORIGINS` เอาไว้เปิดรับ Webhook และโดเมนชั่วคราวแล้ว ได้แก่:

- `*.serveo.net`
- `*.ngrok-free.app`
- `*.ngrok.io` / `*.ngrok.app` / `*.ngrok-free.dev`

**วิธีเจาะทะลุเครือข่ายองค์กร (Bypass FortiGuard):**
หากคุณติด Firewall องค์กรที่บล็อกคำว่า `ngrok` แนะนำให้ใช้ **Serveo**:

```bash
ssh -R 80:localhost:8000 serveo.net
```

ระบบจะสร้างชื่อโดเมน URL มาให้ฟรีๆ ใช้งานได้ทันที

ถ้าคุณแชร์เน็ตจากโทรศัพท์มือถือ (Hotspot) ให้พิมพ์ ngrok ได้ปกติ:

```bash
ngrok http 8000
```

### 8.2 การตั้งค่าความปลอดภัยบน Production

เมื่อตั้ง `DEBUG=False` ควรตรวจสอบ `.env` ดังนี้:

| ตัวแปร          | ค่าที่แนะนำใน Production              |
| --------------- | ------------------------------------- |
| `SECRET_KEY`    | คีย์ลับ 50 ตัวอักษรใหม่               |
| `DEBUG`         | `False`                               |
| `DB_NAME`       | `PostgreSQL` / `MySQL`                |
| `ALLOWED_HOSTS` | โดเมนของบริษัท เช่น `rental.mcot.net` |

---

> **หมายเหตุ:** เอกสารฉบับนี้อัปเดตเพื่อรองรับฟีเจอร์พนักงาน (Summary & Analytics) ธีมใหม่หน้าเว็บบรรยากาศ Glassmorphism การพิมพ์เอกสารแบบเบราว์เซอร์ และการรองรับ Ngrok/Serveo ซึ่งได้นำมาใช้งานแทนเทคโนโลยีเดิมเรียบร้อยแล้ว หากเจาะลึกเฉพาะโค้ด สามารถดูในไฟล์โค้ดได้เลยเนื่องจากมีการทำ Docblock และ Comment ทุกส่วน
