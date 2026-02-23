from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth.models import User

class PasswordManagementTests(TestCase):
    def setUp(self):
        self.username = 'test_user_auth'
        self.password = 'old_password_123'
        self.email = 'testuser@example.com'
        self.user = User.objects.create_user(
            username=self.username, 
            password=self.password,
            email=self.email
        )
        self.client = Client()

    def test_password_change_view_accessible(self):
        """Test that the password change page loads for logged-in users"""
        self.client.login(username=self.username, password=self.password)
        url = reverse('password_change')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'registration/password_change_form.html')

    def test_password_change_redirects_anonymous(self):
        """Test that anonymous users cannot access password change"""
        url = reverse('password_change')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 302)
        self.assertIn('/accounts/login/', response.url)

    def test_password_reset_view_accessible(self):
        """Test that the password reset request page loads"""
        url = reverse('password_reset')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'registration/password_reset_form.html')

    def test_password_reset_email_sent(self):
        """Test submitting the password reset form"""
        from django.core import mail
        url = reverse('password_reset')
        response = self.client.post(url, {'email': self.email})
        
        # Should redirect to password_reset_done
        self.assertRedirects(response, reverse('password_reset_done'))
        
        # Check that one message has been sent.
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn('รหัสผ่าน', mail.outbox[0].subject) # Default Django subject might be different, let's just check it sent
