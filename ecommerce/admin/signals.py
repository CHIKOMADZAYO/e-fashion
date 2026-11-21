from django.db.models.signals import post_save
from django.dispatch import receiver
from django.contrib.auth import get_user_model
from .models import StaffProfile


@receiver(post_save, sender=get_user_model())
def create_staff_profile(sender, instance, created, **kwargs):
    """Auto-create StaffProfile for staff users."""
    if created and instance.is_staff:
        StaffProfile.objects.get_or_create(
            user=instance,
            defaults={
                'role': StaffProfile.Role.SUPERADMIN if instance.is_superuser else StaffProfile.Role.ADMIN,
                'is_active': True,
                'is_approved': instance.is_superuser,
            },
        )


@receiver(post_save, sender=get_user_model())
def save_staff_profile(sender, instance, **kwargs):
    """Save StaffProfile when User is saved."""
    if instance.is_staff:
        StaffProfile.objects.get_or_create(user=instance)
