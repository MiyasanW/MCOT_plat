from django.utils import timezone
from datetime import timedelta, datetime
from django.db.models import Count, Q, Sum
from django.contrib.auth.models import User
from apps.store.models import Booking, Equipment, Studio, Staff, Product, Notification
from django.contrib.admin.models import LogEntry
import json
import logging

logger = logging.getLogger(__name__)

class DashboardService:
    """
    Service สำหรับรวบรวมข้อมูลสถิติและข้อมูลเพื่อแสดงผลใน Dashboard
    ทั้งส่วนของ Admin Dashboard และ Staff Dashboard
    """
    
    @staticmethod
    def get_admin_dashboard_stats():
        """
        รวบรวมสถิติภาพรวมสำหรับ Admin Dashboard
        ประกอบด้วย:
        1. จำนวนการจอง (วันนี้, รออนุมัติ, เดือนนี้)
        2. จำนวนอุปกรณ์และพนักงานที่พร้อมใช้งาน
        3. ยอดรายได้ประจำเดือน
        4. ข้อมูลกราฟรายได้ย้อนหลัง 7 วัน
        5. สัดส่วนสถานะการจอง
        6. อัตราการเติบโตเทียบกับเดือนก่อนหน้า
        """
        today = timezone.now().date()
        
        # 1. Basic Counts (จำนวนพื้นฐาน)
        stats = {
            'bookings_today': Booking.objects.filter(start_time__date=today).count(),
            'bookings_pending': Booking.objects.filter(status='draft').count(),
            'bookings_this_month': Booking.objects.filter(start_time__year=today.year, start_time__month=today.month).count(),
            'equipment_total': Product.objects.count(),
            'equipment_available': Product.objects.filter(is_active=True, quantity__gt=0).count(),
            'staff_active': User.objects.filter(is_staff=True, is_active=True).count(),
        }
        
        # 2. Revenue Calculation (คำนวณรายได้เดือนนี้)
        revenue_this_month = 0
        for booking in Booking.objects.filter(
            start_time__year=today.year, 
            start_time__month=today.month, 
            status__in=['approved', 'completed']
        ):
            revenue_this_month += booking.calculate_total_price()
            
        stats['revenue_this_month'] = revenue_this_month
        
        # 3. Revenue Trend (7 Days) (แนวโน้มรายได้ 7 วันย้อนหลัง)
        days = []
        revenue_trend = []
        for i in range(6, -1, -1):
            d = today - timedelta(days=i)
            days.append(d.strftime('%d %b'))
            daily_rev = 0
            for b in Booking.objects.filter(start_time__date=d, status__in=['approved', 'completed']):
                daily_rev += float(b.calculate_total_price())
            revenue_trend.append(daily_rev)
            
        stats['chart_labels'] = days
        stats['chart_revenue'] = revenue_trend

        # 4. Status Distribution (สัดส่วนสถานะงาน)
        stats['status_counts'] = {
            'draft': Booking.objects.filter(status='draft').count(),
            'approved': Booking.objects.filter(status='approved').count(),
            'completed': Booking.objects.filter(status='completed').count(),
            'active': Booking.objects.filter(status='active').count(),
            'problem': Booking.objects.filter(status='problem').count(),
        }
        
        # 5. Growth Calculation (คำนวณอัตราการเติบโตเทียบเดือนก่อน)
        # Calculate Last Month Revenue
        first_day_this_month = today.replace(day=1)
        last_month_end = first_day_this_month - timedelta(days=1)
        last_month_start = last_month_end.replace(day=1)
        
        revenue_last_month = 0
        for booking in Booking.objects.filter(
            start_time__date__gte=last_month_start,
            start_time__date__lte=last_month_end,
            status__in=['approved', 'completed']
        ):
            revenue_last_month += booking.calculate_total_price()
            
        stats['revenue_last_month'] = revenue_last_month
        
        if revenue_last_month > 0:
            growth = ((revenue_this_month - revenue_last_month) / revenue_last_month) * 100
        else:
            growth = 100 if revenue_this_month > 0 else 0
        stats['revenue_growth'] = round(growth, 1)

        return stats

    @staticmethod
    def get_recent_bookings(limit=5):
        """
        ดึงข้อมูลการจองล่าสุด พร้อมจัดรูปแบบข้อมูลให้พร้อมแสดงผล
        """
        recent_bookings = Booking.objects.select_related('created_by').annotate(
            items_count=Count('items')
        ).order_by('-created_at')[:limit]
        
        clean_bookings = []
        for b in recent_bookings:
            # Resolve Customer Name (หาชื่อลูกค้าจาก User หรือ Username)
            if b.created_by:
                initial = b.created_by.first_name[:1] if b.created_by.first_name else b.created_by.username[:1]
                name = b.created_by.first_name or b.created_by.username
            else:
                initial = "U"
                name = "Unknown"

            clean_bookings.append({
                'id': b.id,
                'customer_initial': initial.upper(),
                'customer_name': name.title(),
                'date_str': b.start_time.strftime('%d %b %Y'),
                'time_str': f"{b.start_time.strftime('%H:%M')} - {b.end_time.strftime('%H:%M')}",
                'total_price': float(b.calculate_total_price()), 
                'items_count': b.items_count,
                'status': b.status,
                'status_display': b.get_status_display(),
                'change_url': f"/admin/rentals/booking/{b.id}/change/"
            })
        return clean_bookings

    @staticmethod
    def get_recent_logs(limit=10):
        """
        ดึงข้อมูล Log การใช้งานระบบล่าสุด (Audit Logs)
        """
        raw_logs = LogEntry.objects.select_related('user', 'content_type').order_by('-action_time')[:limit]
        recent_logs = []
        
        for log in raw_logs:
            message = ""
            try:
                data = json.loads(log.change_message)
                if isinstance(data, list) and data:
                    actions = []
                    for item in data:
                        if 'added' in item:
                            actions.append("Created")
                        elif 'changed' in item:
                            fields = item['changed'].get('fields', [])
                            actions.append(f"Changed: {', '.join(fields)}")
                        elif 'deleted' in item:
                            actions.append("Deleted")
                    message = "; ".join(actions)
            except:
                message = log.change_message or "Changed"
                
            recent_logs.append({
                'user': log.user,
                'user_display': log.user.username.title() if log.user else 'System',
                'object_repr': log.object_repr,
                'action_time': log.action_time,
                'is_addition': log.is_addition(),
                'is_change': log.is_change(),
                'is_deletion': log.is_deletion(),
                'message': message
            })
        return recent_logs
    
    @staticmethod
    def get_staff_dashboard_stats():
        """
        รวบรวมสถิติสำหรับ Staff Dashboard
        (เน้นข้อมูลการปฏิบัติงาน เช่น อุปกรณ์ซ่อม, สตูดิโอ, งานวันนี้)
        """
        today = timezone.now().date()
        stats = {
            'bookings_today': Booking.objects.filter(start_time__date=today).count(),
            'bookings_pending': Booking.objects.filter(status='draft').count(),
            'bookings_this_month': Booking.objects.filter(start_time__year=today.year, start_time__month=today.month).count(),
            'equipment_total': Equipment.objects.count(),
            'equipment_available': Equipment.objects.filter(status='available').count(),
            'equipment_maintenance': Equipment.objects.filter(status='maintenance').count(),
            'studio_total': Studio.objects.count(),
            'staff_active': Staff.objects.filter(is_active=True).count(),
        }
        
        # Revenue
        revenue_this_month = 0
        for booking in Booking.objects.filter(
            start_time__year=today.year,
            start_time__month=today.month,
            status__in=['approved', 'completed']
        ):
            revenue_this_month += booking.calculate_total_price()
        stats['revenue_this_month'] = revenue_this_month
        
        return stats
