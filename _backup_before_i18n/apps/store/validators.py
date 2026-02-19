from django.contrib.auth.password_validation import (
    UserAttributeSimilarityValidator as BaseSimilarityValidator,
    MinimumLengthValidator as BaseLengthValidator,
    CommonPasswordValidator as BaseCommonValidator,
    NumericPasswordValidator as BaseNumericValidator,
)
from django.core.exceptions import ValidationError

class ThaiUserAttributeSimilarityValidator(BaseSimilarityValidator):
    def validate(self, password, user=None):
        try:
            super().validate(password, user)
        except ValidationError:
            raise ValidationError(
                "รหัสผ่านคล้ายกับชื่อผู้ใช้งานหรือข้อมูลส่วนตัวเกินไป",
                code='password_too_similar',
            )

class ThaiMinimumLengthValidator(BaseLengthValidator):
    def validate(self, password, user=None):
        try:
            super().validate(password, user)
        except ValidationError:
            raise ValidationError(
                f"รหัสผ่านสั้นเกินไป ต้องมีอย่างน้อย {self.min_length} ตัวอักษร",
                code='password_too_short',
            )

class ThaiCommonPasswordValidator(BaseCommonValidator):
    def validate(self, password, user=None):
        try:
            super().validate(password, user)
        except ValidationError:
            raise ValidationError(
                "รหัสผ่านนี้เดาง่ายเกินไป กรุณาใช้รหัสที่ซับซ้อนกว่านี้",
                code='password_too_common',
            )

class ThaiNumericPasswordValidator(BaseNumericValidator):
    def validate(self, password, user=None):
        try:
            super().validate(password, user)
        except ValidationError:
            raise ValidationError(
                "รหัสผ่านต้องไม่เป็นตัวเลขเพียงอย่างเดียว",
                code='password_entirely_numeric',
            )
