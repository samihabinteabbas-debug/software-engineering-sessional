from django.contrib import admin
from .models import Vet
from .models import Appointment
from .views import send_confirmation_email,send_cancellation_email,send_completed_email
from .utils import generate_daily_slots
from django import forms
import csv
from django.http import HttpResponse
from django.utils.html import format_html
from django.urls import reverse
from django.contrib.admin import SimpleListFilter

from django.utils import timezone
from datetime import timedelta, datetime


class UpcomingAppointmentFilter(SimpleListFilter):
    title = 'Upcoming appointments'
    parameter_name = 'upcoming'
    
    def lookups(self, request, model_admin):
        return (
            ('today', 'Today'),
            ('tomorrow', 'Tomorrow'),
            ('week', 'Next 7 days'),
            ('month', 'Next 30 days'),
            ('past', 'Past appointments'),
            ('morning', 'Morning (8AM-12PM)'),
            ('afternoon', 'Afternoon (1PM-5PM)'),
        )
    
    def queryset(self, request, queryset):
        now = timezone.now()
        today = now.date()
        
        if self.value() == 'today':
            return queryset.filter(assigned_date=today)
        elif self.value() == 'tomorrow':
            return queryset.filter(assigned_date=today + timedelta(days=1))
        elif self.value() == 'week':
            return queryset.filter(
                assigned_date__range=[today, today + timedelta(days=7)]
            )
        elif self.value() == 'month':
            return queryset.filter(
                assigned_date__range=[today, today + timedelta(days=30)]
            )
        elif self.value() == 'past':
            return queryset.filter(assigned_date__lt=today)
        elif self.value() == 'morning':
            return queryset.filter(
                assigned_time__range=(datetime.strptime('09:00', '%H:%M').time(),
                                     datetime.strptime('12:00', '%H:%M').time())
            )
        elif self.value() == 'afternoon':
            return queryset.filter(
                assigned_time__range=(datetime.strptime('13:00', '%H:%M').time(),
                                     datetime.strptime('17:00', '%H:%M').time())
            )
        return queryset

class AppointmentAdminForm(forms.ModelForm):
    class Meta:
        model = Appointment
        fields = '__all__'

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        if self.instance and self.instance.service:
            self.fields['assigned_doctor'].queryset = Vet.objects.filter(specialty=self.instance.service)


        slot_choices = [(t, t.strftime('%I:%M %p')) for t in generate_daily_slots()]
        self.fields['assigned_time'].widget = forms.Select(choices=slot_choices)
        

        
    def clean(self):
        cleaned_data = super().clean()
        assigned_doctor = cleaned_data.get('assigned_doctor')
        assigned_date = cleaned_data.get('assigned_date')
        assigned_time = cleaned_data.get('assigned_time')

        if assigned_doctor and assigned_date and assigned_time:
            # check if available
            conflict_qs = Appointment.objects.filter(
                assigned_doctor=assigned_doctor,
                assigned_date=assigned_date,
                assigned_time=assigned_time
            )
            if self.instance.pk:
                conflict_qs = conflict_qs.exclude(pk=self.instance.pk)

            if conflict_qs.exists():
                raise forms.ValidationError(
                    f"Dr. {assigned_doctor.name} is already assigned to an appointment at this time."
                )
                             
class AppointmentAdmin(admin.ModelAdmin):
    form = AppointmentAdminForm
    list_display = (
        'appointment_id',
        'assigned_date',
        'assigned_time',
        'assigned_doctor',
        'status_colored',  
        'completion_status',
        'payment_amount',
        'payment_status',
        'view_receipt_link',
        'view_prescription_link',
        'email_link',     
    )

    readonly_fields = ('appointment_id',)
    list_filter = (
        UpcomingAppointmentFilter,
        'status',
        'payment_status',
        'service',
        'completion_status',
        'assigned_doctor'
    )
    search_fields = ('appointment_id', 'owner_name', 'pet_name', 'phone', 'email')

    def status_colored(self, obj):
        colors = {
            'pending': 'yellow',
            'confirmed': 'green',
            'completed': 'blue',
            'cancelled': 'red',
        }
        return format_html(
            '<span style="color:{}; font-weight:bold;">{}</span>',
            colors.get(obj.status, 'black'),
            obj.status.capitalize()
        )
    status_colored.admin_order_field = 'status'
    status_colored.short_description = 'Status'

    def email_link(self, obj):
        if obj.email:
            return format_html(
                '<a href="https://mail.google.com/mail/?view=cm&fs=1&to={}" target="_blank"> {}</a>',
                obj.email,
                obj.email
            )
        return "-"
    email_link.short_description = 'Email'

    def has_prescription(self, obj):
        return bool(obj.prescription.strip())
    has_prescription.boolean = True
    has_prescription.short_description = 'Prescription'
    def view_prescription_link(self, obj):
        if obj.prescription.strip():
            url = reverse('prescription_pdf', args=[obj.appointment_id])
            return format_html('<a class="button" href="{}" target="_blank">Prescription</a>', url)
        return "No prescription"
    view_prescription_link.short_description = 'Prescription'
    
    def save_model(self, request, obj, form, change):
        if change:
            original = Appointment.objects.get(pk=obj.pk)
            if original.status != 'confirmed' and obj.status == 'confirmed':
                send_confirmation_email(obj)
            if original.status != 'cancelled' and obj.status == 'cancelled':
                send_cancellation_email(obj)
            if original.status != 'completed' and obj.status == 'completed':
                send_completed_email(obj)
        super().save_model(request, obj, form, change)
        
    
    actions = ['confirm_selected', 'cancel_selected', 'complete_selected', 'export_as_csv', 'export_prescriptions_csv']
   
    @admin.action(description='Mark selected appointments as completed')
    def complete_selected(self, request, queryset):
        updated = queryset.update(status='completed')
        for appointment in queryset:
            send_completed_email(appointment)
        self.message_user(request, f'{updated} appointments completed.')
    
    @admin.action(description='Mark selected appointments as confirmed')
    def confirm_selected(self, request, queryset):
        updated = queryset.update(status='confirmed')
        for appointment in queryset:
            send_confirmation_email(appointment)
        self.message_user(request, f'{updated} appointments confirmed.')
    
    @admin.action(description='Mark selected appointments as cancelled')
    def cancel_selected(self, request, queryset):
        updated = queryset.update(status='cancelled')
        for appointment in queryset:
            send_cancellation_email(appointment)
        self.message_user(request, f'{updated} appointments cancelled.')
    
    @admin.action(description='Export selected appointments to CSV')
    def export_as_csv(self, request, queryset):
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="appointments.csv"'
        
        writer = csv.writer(response)
        writer.writerow(['ID', 'Owner', 'Pet', 'Date', 'Time', 'Service', 'Doctor', 'Status'])
        
        for obj in queryset:
            writer.writerow([
                obj.appointment_id,
                obj.owner_name,
                obj.pet_name,
                obj.assigned_date.strftime('%Y-%m-%d') if obj.assigned_date else '',
                obj.assigned_time.strftime('%H:%M') if obj.assigned_time else '',
                obj.get_service_display(),
                obj.assigned_doctor.name if obj.assigned_doctor else '',
                obj.get_status_display()
            ])
        
        return response
    
    @admin.action(description='Export prescriptions to CSV')
    def export_prescriptions_csv(self, request, queryset):

        queryset_with_prescriptions = queryset.exclude(prescription='')
        
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="prescriptions.csv"'
        
        writer = csv.writer(response)
        writer.writerow(['Appointment ID', 'Date', 'Owner', 'Pet', 'Doctor', 'Prescription'])
        
        for obj in queryset_with_prescriptions:
            writer.writerow([
                obj.appointment_id,
                obj.assigned_date.strftime('%Y-%m-%d') if obj.assigned_date else obj.preferred_date.strftime('%Y-%m-%d'),
                obj.owner_name,
                obj.pet_name,
                obj.assigned_doctor.name if obj.assigned_doctor else '',
                obj.prescription.replace('\n', ' | ')  
            ])
        
        self.message_user(request, f'Exported {queryset_with_prescriptions.count()} prescriptions.')
        return response
    
    def view_receipt_link(self, obj):
        url = reverse('receipt', args=[obj.appointment_id])
        return format_html('<a class="button" href="{}" target="_blank">Receipt</a>', url)
    view_receipt_link.short_description = 'Receipt'
    
    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == "assigned_doctor":
            try:
                appointment_id = request.resolver_match.kwargs.get('object_id')
                if appointment_id:
                    appointment = Appointment.objects.get(pk=appointment_id)
                    kwargs["queryset"] = Vet.objects.filter(specialty=appointment.service)
            except:
                pass
        return super().formfield_for_foreignkey(db_field, request, **kwargs)
        
    date_hierarchy = 'assigned_date'

    def get_form(self, request, obj=None, **kwargs):
        request._obj_ = obj
        return super().get_form(request, obj, **kwargs)

admin.site.register(Appointment, AppointmentAdmin)


@admin.register(Vet)
class VetAdmin(admin.ModelAdmin):
    list_display = ('name', 'specialty', 'email', 'phone', 'linked_user', 'appointment_count')
    list_filter = ('specialty',)
    search_fields = ('name', 'email')

    fields = ('name', 'specialty', 'email', 'phone', 'bio', 'photo_url', 'user')
    
    def linked_user(self, obj):
        if obj.user:
            return f"{obj.user.username} ({obj.user.first_name} {obj.user.last_name})"
        return "No user account"
    linked_user.short_description = 'User Account'
    
    def appointment_count(self, obj):
        return obj.appointment_set.count()
    appointment_count.short_description = 'Appointments'