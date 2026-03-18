import json
from datetime import timedelta

from django.contrib.auth.models import User
from django.test import Client, TestCase
from django.urls import reverse
from django.utils import timezone

from apps.store.models import Booking, BookingItem, Product, ProductCategory


class BookingStateTransitionTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.staff = User.objects.create_user(
            username="staff_transition",
            password="password123",
            is_staff=True,
        )
        self.customer = User.objects.create_user(
            username="customer_transition",
            password="password123",
        )

        self.booking = Booking.objects.create(
            created_by=self.customer,
            customer_name="Transition Customer",
            phone="0812345678",
            start_time=timezone.now() + timedelta(days=1),
            end_time=timezone.now() + timedelta(days=2),
            status="draft",
            payment_status="pending",
        )

        self.action_url = reverse(
            "store:api_staff_booking_action", kwargs={"booking_id": self.booking.id}
        )

    def post_action(self, action):
        self.client.login(username="staff_transition", password="password123")
        return self.client.post(
            self.action_url,
            data=json.dumps({"action": action}),
            content_type="application/json",
        )

    def test_mark_active_requires_paid_or_waived_when_pending(self):
        response = self.post_action("mark_active")
        self.assertEqual(response.status_code, 400)
        self.booking.refresh_from_db()
        self.assertEqual(self.booking.status, "draft")

    def test_confirm_payment_accepts_unpaid_and_then_mark_active(self):
        self.booking.status = "pending"
        self.booking.payment_status = "unpaid"
        self.booking.save(update_fields=["status", "payment_status"])

        response_confirm = self.post_action("confirm_payment")
        self.assertEqual(response_confirm.status_code, 200)

        self.booking.refresh_from_db()
        self.assertEqual(self.booking.payment_status, "paid")

        response_active = self.post_action("mark_active")
        self.assertEqual(response_active.status_code, 200)

        self.booking.refresh_from_db()
        self.assertEqual(self.booking.status, "active")

    def test_mark_completed_requires_active_or_overdue(self):
        self.booking.status = "approved"
        self.booking.save(update_fields=["status"])

        response = self.post_action("mark_completed")
        self.assertEqual(response.status_code, 400)
        self.booking.refresh_from_db()
        self.assertEqual(self.booking.status, "approved")

    def test_valid_flow_approved_to_active_to_completed(self):
        self.booking.status = "approved"
        self.booking.save(update_fields=["status"])

        response_active = self.post_action("mark_active")
        self.assertEqual(response_active.status_code, 200)

        self.booking.refresh_from_db()
        self.assertEqual(self.booking.status, "active")

        response_completed = self.post_action("mark_completed")
        self.assertEqual(response_completed.status_code, 200)

        self.booking.refresh_from_db()
        self.assertEqual(self.booking.status, "completed")

    def test_mark_active_requires_equipment_assignment(self):
        category = ProductCategory.objects.create(name="กล้อง", slug="camera-test")
        product = Product.objects.create(name="Test Camera", category=category, price=1000, quantity=1)
        BookingItem.objects.create(booking=self.booking, product=product, quantity=1, price_at_booking=1000)

        self.booking.status = "pending"
        self.booking.payment_status = "paid"
        self.booking.save(update_fields=["status", "payment_status"])

        response = self.post_action("mark_active")
        self.assertEqual(response.status_code, 400)
        self.assertIn("assign Serial/Asset", response.json().get("message", ""))

        self.booking.refresh_from_db()
        self.assertEqual(self.booking.status, "pending")
