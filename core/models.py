from django.db import models
from django.contrib.auth.models import User
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.utils import timezone

from django.db import models

class Vet(models.Model):
    DEPARTMENTS = [
        ('Preventive Care', 'Preventive Care'),
        ('Surgical Procedures', 'Surgical Procedures'),
        ('Dental Care', 'Dental Care'),
        ('Diagnostic Imaging', 'Diagnostic Imaging'),
        ('Emergency Services', 'Emergency Services'),
        ('Nutritional Counseling', 'Nutritional Counseling'),
    ]

    name = models.CharField(max_length=100)
    specialty = models.CharField(max_length=50, choices=DEPARTMENTS)
    email = models.EmailField()
    phone = models.CharField(max_length=20)
    bio = models.TextField(blank=True)
    photo_url = models.CharField(max_length=255, blank=True)  # for relative static path
    user = models.OneToOneField(User, on_delete=models.CASCADE, null=True, blank=True)  # NEW FIELD

    def __str__(self):
        return self.name


class Profile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    full_name = models.CharField(max_length=150, blank=True)
    address = models.TextField(blank=True)
    email = models.EmailField(blank=True)
    phone = models.CharField(max_length=20, blank=True)

    def __str__(self):
        return f"Profile of {self.user.username}"


@receiver(post_save, sender=User)
def create_or_update_user_profile(sender, instance, created, **kwargs):
    if created:

        if not hasattr(instance, 'vet'):
            Profile.objects.create(user=instance)
    else:
        if hasattr(instance, 'profile'):
            instance.profile.save()


class Appointment(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending Confirmation'),
        ('confirmed', 'Confirmed'),
        ('cancelled', 'Cancelled'),
        ('completed', 'Completed'),
    ]

    SERVICE_CHOICES = [
        ('Preventive Care', 'Preventive Care'),
        ('Surgical Procedures', 'Surgical Procedures'),
        ('Dental Care', 'Dental Care'),
        ('Diagnostic Imaging', 'Diagnostic Imaging'),
        ('Emergency Services', 'Emergency Services'),
        ('Nutritional Counseling', 'Nutritional Counseling'),
    ]
    
    SPECIES_CHOICES = [
        ('dog', 'Dog'),
        ('cat', 'Cat'),
        ('bird', 'Bird'),
        ('rabbit', 'Rabbit'),
        ('other', 'Other'),
    ]
    COMPLETION_STATUS_CHOICES = [
    ('incomplete', 'Incomplete'),
    ('complete', 'Complete'),
]


    completion_status = models.CharField(
        max_length=10, 
        choices=COMPLETION_STATUS_CHOICES, 
        default='incomplete',
        verbose_name="Completion Status"
    )
        
    appointment_id = models.CharField(
        max_length=12, unique=True, editable=False, default='', blank=True
    )
    owner_name = models.CharField(max_length=100)
    phone = models.CharField(max_length=20)
    email = models.EmailField(blank=True)
    pet_name = models.CharField(max_length=100)
    pet_species = models.CharField(max_length=20, choices=SPECIES_CHOICES)
    pet_age = models.CharField(max_length=20, blank=True, verbose_name="Pet Age")
    pet_weight = models.CharField(max_length=20, blank=True, verbose_name="Pet Weight (kg)")
    preferred_date = models.DateField()
    preferred_time = models.TimeField()
    reason = models.TextField(blank=True)
    service = models.CharField(max_length=40, choices=SERVICE_CHOICES)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='pending')
    assigned_doctor = models.ForeignKey('Vet', on_delete=models.SET_NULL, null=True, blank=True)
    assigned_time = models.TimeField(null=True, blank=True)
    assigned_date = models.DateField(null=True, blank=True)
    prescription = models.TextField(blank=True, verbose_name="Prescription/Notes")
    
    PAYMENT_STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('paid', 'Paid'),
        ('refunded', 'Refunded'),
    ]

    payment_amount = models.DecimalField(
        max_digits=8, decimal_places=2, null=True, blank=True, verbose_name="Payment Amount"
    )
    payment_status = models.CharField(
        max_length=10,
        choices=PAYMENT_STATUS_CHOICES,
        default='pending',
        verbose_name="Payment Status"
    )
    
    def __str__(self):
        return f"{self.owner_name} - {self.appointment_id}"

    def save(self, *args, **kwargs):
        if not self.appointment_id:
            self.appointment_id = self.generate_unique_id()
        super().save(*args, **kwargs)

    def generate_unique_id(self):
        from random import choices
        import string
        while True:
            unique_id = ''.join(choices(string.ascii_uppercase + string.digits, k=8))
            if not Appointment.objects.filter(appointment_id=unique_id).exists():
                return unique_id

    @property
    def display_time(self):
        if self.assigned_date and self.assigned_time:
            return f"{self.assigned_date.strftime('%B %d, %Y')} at {self.assigned_time.strftime('%I:%M %p')}"
        return f"{self.preferred_date.strftime('%B %d, %Y')} at {self.preferred_time.strftime('%I:%M %p')} (Requested)"

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['preferred_date', 'preferred_time'], name='unique_preferred_slot')
        ]