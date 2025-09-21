from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.auth import authenticate, logout, login
from django.contrib.auth.models import User
from django.contrib import messages
from .models import Appointment, Vet
from datetime import datetime, date, timedelta
import uuid
from django.contrib.admin.views.decorators import staff_member_required
from django.core.mail import send_mail
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
import io
from django.http import JsonResponse, FileResponse 

@staff_member_required
def prescription_pdf_view(request, appointment_id):
    appointment = get_object_or_404(Appointment, appointment_id=appointment_id)
    buffer = io.BytesIO()

    p = canvas.Canvas(buffer, pagesize=letter)
    width, height = letter
    
    #clinic header
    p.setFont("Helvetica-Bold", 16)
    p.drawString(100, height - 100, "Crescent Veterinary Clinic")
    p.setFont("Helvetica", 10)
    p.drawString(100, height - 120, "Professional Veterinary Services")
    p.drawString(100, height - 140, "Phone: +8801111111111 | Email: info@crescentvet.com")
    
    
    #patient info
    p.setFont("Helvetica-Bold", 14)
    p.drawString(100, height - 180, "PATIENT INFORMATION")
    p.line(100, height - 185, 500, height - 185)
    
    p.setFont("Helvetica", 10)
    y_position = height - 210
    p.drawString(100, y_position, f"Pet Name: {appointment.pet_name}")
    p.drawString(300, y_position, f"Species: {appointment.get_pet_species_display()}")
    
    y_position -= 20
    p.drawString(100, y_position, f"Owner: {appointment.owner_name}")
    p.drawString(300, y_position, f"Phone: {appointment.phone}")
    
    y_position -= 20
    p.drawString(100, y_position, f"Service: {appointment.service}")
    p.drawString(300, y_position, f"Appointment ID: {appointment.appointment_id}")
    
    # Prescription
    if appointment.prescription:
        y_position -= 40
        p.setFont("Helvetica-Bold", 14)
        p.drawString(100, y_position, "PRESCRIPTION")
        p.line(100, y_position - 5, 500, y_position - 5)
        
        p.setFont("Helvetica", 10)
        y_position -= 30

        lines = appointment.prescription.split('\n')
        for line in lines:
            if y_position < 100: 
                p.showPage()
                p.setFont("Helvetica", 10)
                y_position = height - 100
            
            p.drawString(100, y_position, line)
            y_position -= 15
            
            
    if appointment.assigned_doctor:

        y_position -= 100 
        p.drawString(100, y_position, f"Dr. {appointment.assigned_doctor.name}")    
        y_position -= 15  
        p.line(100, y_position, 250, y_position)  
        y_position -= 15
        p.drawString(100, y_position, "Signature")

    
    p.drawString(400, y_position - 20, f"Date: {appointment.assigned_date.strftime('%B %d, %Y') if appointment.assigned_date else 'N/A'}")
    p.showPage()
    p.save()
    buffer.seek(0)
    return FileResponse(buffer, as_attachment=False, filename=f"prescription_{appointment_id}.pdf")

@login_required
def doctor_dashboard(request):
    if not hasattr(request.user, 'vet'):
        messages.error(request, "Access denied. You are not authorized to view this page.")
        return redirect('home')
    
    doctor = request.user.vet
    today = date.today()
    
    todays_appointments = Appointment.objects.filter(
        assigned_doctor=doctor,
        assigned_date=today,
        status="confirmed"
    ).order_by('assigned_time')
    

    upcoming_appointments = Appointment.objects.filter(
        assigned_doctor=doctor,
        assigned_date__gt=today,
        assigned_date__lte=today + timedelta(days=7),
        status="confirmed"
    ).order_by('assigned_date', 'assigned_time')
    
    context = {
        'doctor': doctor,
        'today': today,
        'todays_appointments': todays_appointments,
        'upcoming_appointments': upcoming_appointments,
    }
    
    return render(request, 'doctor_dashboard.html', context)


@login_required
@require_POST
def save_prescription(request, appointment_id):
    if not hasattr(request.user, 'vet'):
        return JsonResponse({'success': False, 'error': 'Unauthorized'})
    
    appointment = get_object_or_404(Appointment, appointment_id=appointment_id)
    
    if appointment.assigned_doctor != request.user.vet:
        return JsonResponse({'success': False, 'error': 'Not your appointment'})
    
    chief_complaint = request.POST.get('chief_complaint', '').strip()
    diagnosis = request.POST.get('diagnosis', '').strip()
    medications = request.POST.get('medications', '').strip()
    instructions = request.POST.get('instructions', '').strip()
    follow_up = request.POST.get('follow_up', '').strip()
    mark_complete = request.POST.get('mark_complete', 'false') == 'true'
    
    prescription_parts = []
    
    if chief_complaint:
        prescription_parts.append(f"CHIEF COMPLAINT:\n{chief_complaint}")
    
    if diagnosis:
        prescription_parts.append(f"DIAGNOSIS:\n{diagnosis}")
    
    if medications:
        prescription_parts.append(f"PRESCRIPTION (Rx):\n{medications}")
    
    if instructions:
        prescription_parts.append(f"INSTRUCTIONS:\n{instructions}")
    
    if follow_up:
        prescription_parts.append(f"FOLLOW-UP:\n{follow_up}")
    
    full_prescription = "\n\n".join(prescription_parts)
    
    appointment.prescription = full_prescription
    
    # Update completion status if requested
    if mark_complete:
        appointment.completion_status = 'complete'
        appointment.status = 'completed'
    
    appointment.save()
    
    return JsonResponse({'success': True, 'message': 'Prescription saved successfully'})
def home(request):
    return render(request, 'index.html')

def services(request):
    return render(request, 'services.html')

def prevcare(request):
    return render(request, 'prevcare.html')

def surg(request):
    return render(request, 'surg.html')

def dent(request):
    return render(request, 'dent.html')

def diag(request):
    return render(request, 'diag.html')

def emer(request):
    return render(request, 'emer.html')

def nutri(request):
    return render(request, 'nutri.html')

def login_view(request):
    if request.method == "POST":
        username = request.POST.get('username')
        password = request.POST.get('password')
        user = authenticate(request, username=username, password=password)
        
        if user is not None:
            login(request, user)

            try:
                if hasattr(user, 'vet'):
                    return redirect('doctor_dashboard')
            except:
                pass

            return redirect('home')
        else:
            if User.objects.filter(username=username).exists():
                messages.error(request, "Incorrect password.")
            else:
                messages.error(request, "Username does not exist.")
    
    return render(request, 'login.html')

def signup_view(request):
    if request.method == "POST":
        username = request.POST.get('username')
        password = request.POST.get('password')
        first_name = request.POST.get('first_name', '').strip()
        last_name = request.POST.get('last_name', '').strip()
        email = request.POST.get('email', '').strip()

        if not username or not password or not email:
            messages.error(request, "Username, email, and password are required.")
        elif User.objects.filter(username=username).exists():
            messages.error(request, "Username already exists.")
        elif User.objects.filter(email=email).exists():
            messages.error(request, "An account with this email already exists.")
        else:
            user = User.objects.create_user(username=username, password=password, email=email)
            user.first_name = first_name
            user.last_name = last_name
            user.save()

            profile = user.profile
            profile.full_name = first_name +' '+ last_name
            profile.email = email
            profile.save()

            login(request, user)
            return redirect('home')

    return render(request, 'signup.html')


@login_required
def appointment_view(request):
    if request.method == 'POST':
        owner_name = request.POST.get('owner_name')
        phone = request.POST.get('owner_phone')
        email = request.user.email
        pet_name = request.POST.get('pet_name')
        pet_species = request.POST.get('pet_species')
        pet_age = request.POST.get('pet_age', '')
        pet_weight = request.POST.get('pet_weight', '')
        service = request.POST.get('service')
        preferred_date = request.POST.get('appointment_date')
        preferred_time = request.POST.get('appointment_time')
        reason = request.POST.get('reason')
        appointment_id = str(uuid.uuid4())[:8].upper()

        Appointment.objects.create(
            appointment_id=appointment_id,
            owner_name=owner_name,
            phone=phone,
            email=email,
            pet_name=pet_name,
            pet_species=pet_species,
            pet_age=pet_age,
            pet_weight=pet_weight,
            service=service,
            preferred_date=preferred_date,
            preferred_time=preferred_time,
            reason=reason,
        )
        return redirect('profile')

    context = {
        'today_date': datetime.today(),
    }
    return render(request, 'appt.html', context)


def logout_view(request):
    logout(request)
    return redirect('home')


@login_required
def appt(request):
    return render(request, 'appt.html', {'today_date': datetime.today()})


@login_required
def profile_view(request):
    user = request.user
    appointments = Appointment.objects.filter(email=user.email).order_by('-assigned_date', '-assigned_time', '-preferred_date', '-preferred_time')

    
    return render(request, 'profile.html', {
        'appointments': appointments,
        'user': user,
    })


def our_team_view(request):
    doctors = Vet.objects.all()
    return render(request, 'ourteam.html', {'doctors': doctors})


@staff_member_required
def receipt_view(request, appointment_id):
    appointment = get_object_or_404(Appointment, appointment_id=appointment_id)
    return render(request, 'receipt.html', {'appointment': appointment})


@login_required
def doctor_dashboard(request):

    if not hasattr(request.user, 'vet'):
        messages.error(request, "Access denied. You are not authorized to view this page.")
        return redirect('home')
    
    doctor = request.user.vet
    today = date.today()
    
        
    todays_appointments = Appointment.objects.filter(
        assigned_doctor=doctor,
        assigned_date=today,
        status='confirmed'
    ).order_by('assigned_time')
    

    upcoming_appointments = Appointment.objects.filter(
        assigned_doctor=doctor,
        assigned_date__gt=today,
        assigned_date__lte=today + timedelta(days=7),
        status='confirmed'
    ).order_by('assigned_date', 'assigned_time')
    
    context = {
        'doctor': doctor,
        'today': today,
        'todays_appointments': todays_appointments,
        'upcoming_appointments': upcoming_appointments,
    }
    
    return render(request, 'doctor_dashboard.html', context)


@login_required
@require_POST
def save_prescription(request, appointment_id):
    if not hasattr(request.user, 'vet'):
        return JsonResponse({'success': False, 'error': 'Unauthorized'})
    
    appointment = get_object_or_404(Appointment, appointment_id=appointment_id)
    
    if appointment.assigned_doctor != request.user.vet:
        return JsonResponse({'success': False, 'error': 'Not your appointment'})
    
    chief_complaint = request.POST.get('chief_complaint', '').strip()
    diagnosis = request.POST.get('diagnosis', '').strip()
    medications = request.POST.get('medications', '').strip()
    instructions = request.POST.get('instructions', '').strip()
    follow_up = request.POST.get('follow_up', '').strip()
    mark_complete = request.POST.get('mark_complete') == 'true'  # Fix this line
    
    prescription_parts = []
    
    if chief_complaint:
        prescription_parts.append(f"CHIEF COMPLAINT:\n{chief_complaint}")
    
    if diagnosis:
        prescription_parts.append(f"DIAGNOSIS:\n{diagnosis}")
    
    if medications:
        prescription_parts.append(f"PRESCRIPTION (Rx):\n{medications}")
    
    if instructions:
        prescription_parts.append(f"INSTRUCTIONS:\n{instructions}")
    
    if follow_up:
        prescription_parts.append(f"FOLLOW-UP:\n{follow_up}")
    
    full_prescription = "\n\n".join(prescription_parts)
    
    appointment.prescription = full_prescription
    

    if mark_complete:
        appointment.completion_status = 'complete'
    else:
        appointment.completion_status = 'incomplete'
    
    appointment.save()
    
    return JsonResponse({'success': True, 'message': 'Prescription saved successfully'})

@login_required
def get_prescription_data(request, appointment_id):
    """Get prescription templates and drug database for the modal"""
    if not hasattr(request.user, 'vet'):
        return JsonResponse({'error': 'Unauthorized'}, status=403)
    

    templates = {
        'antibiotics': {
            'name': 'Bacterial Infection',
            'diagnosis': 'Bacterial infection',
            'medications': '''1. Amoxicillin 250mg
   Sig: Give 1 capsule by mouth twice daily for 10 days
   
2. Probiotics
   Sig: Give 1 capsule by mouth once daily during antibiotic treatment''',
            'instructions': 'Give with food to reduce stomach upset. Complete full course even if symptoms improve.',
            'follow_up': 'Return in 10-14 days for recheck if symptoms persist'
        },
        'pain_inflammation': {
            'name': 'Pain & Inflammation',
            'diagnosis': 'Pain and inflammation',
            'medications': '''1. Carprofen 75mg
   Sig: Give 1 tablet by mouth once daily with food for 5-7 days
   
2. Gabapentin 100mg (if severe pain)
   Sig: Give 1 capsule by mouth twice daily as needed''',
            'instructions': 'Monitor for appetite changes or vomiting. Discontinue if side effects occur.',
            'follow_up': 'Return if no improvement in 3-5 days or if condition worsens'
        },
        'skin_condition': {
            'name': 'Skin Condition',
            'diagnosis': 'Dermatitis/skin irritation',
            'medications': '''1. Medicated shampoo
   Sig: Bathe twice weekly, leave on for 10 minutes before rinsing
   
2. Topical cream
   Sig: Apply thin layer to affected areas twice daily''',
            'instructions': 'Keep area clean and dry. Prevent licking with cone if necessary.',
            'follow_up': 'Return in 7-10 days for progress evaluation'
        },
        'dental': {
            'name': 'Dental Care',
            'diagnosis': 'Dental disease/tartar buildup',
            'medications': '''1. Dental chews (prescription)
   Sig: Give 1 chew daily
   
2. Oral rinse
   Sig: Add to water bowl as directed''',
            'instructions': 'Begin regular tooth brushing routine. Avoid hard bones or toys.',
            'follow_up': 'Schedule dental cleaning in 6 months'
        },
        'parasite': {
            'name': 'Parasite Treatment',
            'diagnosis': 'Intestinal parasites',
            'medications': '''1. Deworming medication
   Sig: Give as directed based on body weight
   
2. Fecal exam in 2-3 weeks''',
            'instructions': 'Pick up stool immediately. Wash hands after handling pet.',
            'follow_up': 'Bring fresh stool sample in 2-3 weeks for recheck'
        },
        'allergy': {
            'name': 'Allergy Management',
            'diagnosis': 'Environmental allergies',
            'medications': '''1. Apoquel 5.4mg
   Sig: Give 1 tablet by mouth twice daily for 7 days, then once daily
   
2. Antihistamine
   Sig: Give 1 tablet by mouth once daily as needed for itching''',
            'instructions': 'Reduce exposure to allergens. Bathe weekly with hypoallergenic shampoo.',
            'follow_up': 'Return in 3-4 weeks for progress evaluation'
        },
        'ear_infection': {
            'name': 'Ear Infection',
            'diagnosis': 'Otitis externa',
            'medications': '''1. Ear cleaner
   Sig: Clean ears twice weekly
   
2. Antibiotic/steroid ear drops
   Sig: Apply 5 drops in affected ear twice daily for 7 days''',
            'instructions': 'Keep ears dry. Do not use cotton swabs in ear canal.',
            'follow_up': 'Return in 7-10 days for recheck'
        },
        'anxiety': {
            'name': 'Anxiety Treatment',
            'diagnosis': 'Generalized anxiety',
            'medications': '''1. Trazodone 100mg
   Sig: Give 1/2 to 1 tablet by mouth as needed for anxiety
   
2. Adaptil diffuser
   Sig: Use continuously in main living area''',
            'instructions': 'Provide safe space. Use calming music during stressful events.',
            'follow_up': 'Return in 4 weeks for behavior assessment'
        }
    }
    
    # Expanded medications database
    medications_db = [
        {'name': 'Acepromazine', 'strengths': ['10mg', '25mg'], 'type': 'Sedative'},
    {'name': 'Amoxicillin', 'strengths': ['250mg', '500mg'], 'type': 'Antibiotic'},
    {'name': 'Amitriptyline', 'strengths': ['10mg', '25mg'], 'type': 'Behavioral'},
    {'name': 'Apoquel', 'strengths': ['3.6mg', '5.4mg', '16mg'], 'type': 'Anti-itch'},
    {'name': 'Benazepril', 'strengths': ['2.5mg', '5mg', '10mg', '20mg'], 'type': 'Cardiac'},
    {'name': 'Bravecto', 'strengths': ['112.5mg', '250mg', '500mg'], 'type': 'Flea/Tick Prevention'},
    {'name': 'Buprenorphine', 'strengths': ['0.3mg/ml'], 'type': 'Pain Management'},
    {'name': 'Butorphanol', 'strengths': ['5mg/ml', '10mg/ml'], 'type': 'Pain Management'},
    {'name': 'Carprofen', 'strengths': ['25mg', '75mg', '100mg'], 'type': 'Anti-inflammatory'},
    {'name': 'Cefpodoxime', 'strengths': ['100mg', '200mg'], 'type': 'Antibiotic'},
    {'name': 'Cephalexin', 'strengths': ['250mg', '500mg'], 'type': 'Antibiotic'},
    {'name': 'Cerenia', 'strengths': ['16mg', '24mg', '60mg'], 'type': 'Anti-nausea'},
    {'name': 'Chloramphenicol', 'strengths': ['100mg', '250mg', '500mg'], 'type': 'Antibiotic'},
    {'name': 'Clavamox', 'strengths': ['62.5mg', '125mg', '250mg'], 'type': 'Antibiotic'},
    {'name': 'Clindamycin', 'strengths': ['25mg', '75mg', '150mg'], 'type': 'Antibiotic'},
    {'name': 'Cyclosporine', 'strengths': ['10mg', '25mg', '50mg', '100mg'], 'type': 'Immunosuppressant'},
    {'name': 'Denamarin', 'strengths': ['100mg', '225mg'], 'type': 'Liver Support'},
    {'name': 'Diazepam', 'strengths': ['2mg', '5mg', '10mg'], 'type': 'Behavioral'},
    {'name': 'Diphenhydramine', 'strengths': ['25mg'], 'type': 'Antihistamine'},
    {'name': 'Doxycycline', 'strengths': ['50mg', '100mg'], 'type': 'Antibiotic'},
    {'name': 'Enalapril', 'strengths': ['2.5mg', '5mg', '10mg', '20mg'], 'type': 'Cardiac'},
    {'name': 'Enrofloxacin', 'strengths': ['22.7mg', '68mg'], 'type': 'Antibiotic'},
    {'name': 'Famotidine', 'strengths': ['10mg'], 'type': 'Stomach Protection'},
    {'name': 'Fluoxetine', 'strengths': ['10mg', '20mg'], 'type': 'Behavioral'},
    {'name': 'Furosemide', 'strengths': ['12.5mg', '25mg', '50mg'], 'type': 'Diuretic'},
    {'name': 'Gabapentin', 'strengths': ['100mg', '300mg'], 'type': 'Pain Management'},
    {'name': 'Glipizide', 'strengths': ['5mg'], 'type': 'Diabetes'},
    {'name': 'Hydrochlorothiazide', 'strengths': ['12.5mg', '25mg'], 'type': 'Diuretic'},
    {'name': 'Hydroxyzine', 'strengths': ['10mg', '25mg'], 'type': 'Antihistamine'},
    {'name': 'Insulin (Vetsulin)', 'strengths': ['40U/ml'], 'type': 'Diabetes'},
    {'name': 'Itraconazole', 'strengths': ['100mg'], 'type': 'Antifungal'},
    {'name': 'Ivermectin', 'strengths': ['68mcg', '136mcg'], 'type': 'Heartworm Prevention'},
    {'name': 'Ketoconazole', 'strengths': ['200mg'], 'type': 'Antifungal'},
    {'name': 'Levetiracetam', 'strengths': ['250mg', '500mg'], 'type': 'Seizure'},
    {'name': 'Marbofloxacin', 'strengths': ['25mg', '50mg', '100mg'], 'type': 'Antibiotic'},
    {'name': 'Maropitant', 'strengths': ['16mg', '24mg', '60mg'], 'type': 'Anti-nausea'},
    {'name': 'Meloxicam', 'strengths': ['1.5mg/ml'], 'type': 'Anti-inflammatory'},
    {'name': 'Metronidazole', 'strengths': ['250mg', '500mg'], 'type': 'Antibiotic/Anti-diarrheal'},
    {'name': 'Methimazole', 'strengths': ['2.5mg', '5mg'], 'type': 'Thyroid'},
    {'name': 'Milbemycin', 'strengths': ['2.3mg', '5.75mg', '11.5mg'], 'type': 'Heartworm Prevention'},
    {'name': 'Mirtazapine', 'strengths': ['7.5mg', '15mg'], 'type': 'Appetite Stimulant'},
    {'name': 'Omeprazole', 'strengths': ['10mg', '20mg'], 'type': 'Stomach Protection'},
    {'name': 'Ondansetron', 'strengths': ['4mg', '8mg'], 'type': 'Anti-nausea'},
    {'name': 'Orbifloxacin', 'strengths': ['5.7mg', '22.7mg', '68mg'], 'type': 'Antibiotic'},
    {'name': 'Phenobarbital', 'strengths': ['16.2mg', '32.4mg', '64.8mg'], 'type': 'Seizure'},
    {'name': 'Pimobendan', 'strengths': ['1.25mg', '2.5mg', '5mg'], 'type': 'Cardiac'},
    {'name': 'Praziquantel', 'strengths': ['34mg', '136mg'], 'type': 'Dewormer'},
    {'name': 'Prednisone', 'strengths': ['5mg', '10mg', '20mg'], 'type': 'Steroid'},
    {'name': 'Pyrantel', 'strengths': ['50mg/ml'], 'type': 'Dewormer'},
    {'name': 'Revolution', 'strengths': ['15mg', '30mg', '45mg'], 'type': 'Parasite Prevention'},
    {'name': 'Rimadyl', 'strengths': ['25mg', '75mg', '100mg'], 'type': 'Anti-inflammatory'},
    {'name': 'Samylin', 'strengths': ['100mg', '200mg'], 'type': 'Liver Support'},
    {'name': 'Sildenafil', 'strengths': ['20mg', '25mg', '50mg', '100mg'], 'type': 'Cardiac'},
    {'name': 'Simparica', 'strengths': ['5mg', '10mg', '20mg'], 'type': 'Flea/Tick Prevention'},
    {'name': 'Spironolactone', 'strengths': ['25mg', '50mg', '100mg'], 'type': 'Diuretic'},
    {'name': 'Sucralfate', 'strengths': ['1g'], 'type': 'Stomach Protection'},
    {'name': 'Terbinafine', 'strengths': ['250mg'], 'type': 'Antifungal'},
    {'name': 'Tramadol', 'strengths': ['50mg'], 'type': 'Pain Management'},
    {'name': 'Trazodone', 'strengths': ['50mg', '100mg'], 'type': 'Behavioral'},
    {'name': 'Thyroxine', 'strengths': ['0.1mg', '0.2mg', '0.3mg', '0.4mg', '0.5mg', '0.6mg', '0.7mg', '0.8mg'], 'type': 'Thyroid'},
    {'name': 'Yunnan Baiyao', 'strengths': ['250mg'], 'type': 'Hemostatic'}
    ]
    
    return JsonResponse({
        'templates': templates,
        'medications': medications_db,
        'success': True
    })


#EMAIL
def send_cancellation_email(appointment):
    subject = "Your Appointment Has Been Cancelled"

    message = f"""Dear {appointment.owner_name or 'Valued Client'},

We regret to inform you that your appointment (ID: {appointment.appointment_id}) for {appointment.pet_name}, scheduled for {appointment.assigned_date or appointment.preferred_date} at {appointment.assigned_time or appointment.preferred_time} has been cancelled.
For more information, please contact us at +8801111111111 or reply to this email.

We apologize for any inconvenience.

Best regards,  
The Crescent Veterinary Clinic Team
"""

    recipient_list = [appointment.email]
    send_mail(
        subject,
        message,
        None,
        recipient_list,
        fail_silently=True
    )

def send_completed_email(appointment):
    subject = "Your Appointment is Completed!"

    message = f"""Dear {appointment.owner_name or 'Valued Client'},

Your appointment (ID: {appointment.appointment_id}) for {appointment.pet_name}, scheduled for {appointment.assigned_date or appointment.preferred_date} at {appointment.assigned_time or appointment.preferred_time} has been completed.
Thank you for being with us!

Keep in touch with us for updates, pet care tips and more-
Facebook: https://facebook.com/crescentveterinaryclinic
Instagram: https://instagram.com/crescentveterinaryclinic
X: https://x.com/crescentveterinaryclinic

Best regards,  
The Crescent Veterinary Clinic Team
"""

    recipient_list = [appointment.email]
    send_mail(
        subject,
        message,
        None,  
        recipient_list,
        fail_silently=True
    )

def send_confirmation_email(appointment):
    subject = "Your Appointment is Confirmed"
    
    vet_line = ""
    if appointment.assigned_doctor and appointment.assigned_doctor.name:
        vet_line = f"\nVeterinarian assigned: Dr. {appointment.assigned_doctor.name}"
    
    message = f"""Dear {appointment.owner_name or 'Valued Client'},

Your appointment (ID: {appointment.appointment_id}) for {appointment.pet_name} has been confirmed.

📅 Appointment Details:
Date: {appointment.assigned_date or appointment.preferred_date}
Time: {appointment.assigned_time or appointment.preferred_time}{vet_line}

Please arrive 10 minutes early to complete any necessary paperwork.

If you need to reschedule or have any questions, please contact us at +8801111111111 or reply to this email.

Warm regards,  
The Crescent Veterinary Clinic Team
"""

    recipient_list = [appointment.email]
    send_mail(
        subject,
        message,
        None,  
        recipient_list,
        fail_silently=True
    )
    
    
@login_required
def get_existing_prescription(request, appointment_id):
    """Get existing prescription data for editing"""
    if not hasattr(request.user, 'vet'):
        return JsonResponse({'error': 'Unauthorized'}, status=403)
    
    appointment = get_object_or_404(Appointment, appointment_id=appointment_id)
    if appointment.assigned_doctor != request.user.vet:
        return JsonResponse({'error': 'Not your appointment'}, status=403)
    

    prescription_text = appointment.prescription
    chief_complaint = ""
    diagnosis = ""
    medications = ""
    instructions = ""
    follow_up = ""
    
    if prescription_text:
        parts = prescription_text.split('\n\n')
        for part in parts:
            if part.startswith('CHIEF COMPLAINT:'):
                chief_complaint = part.replace('CHIEF COMPLAINT:\n', '')
            elif part.startswith('DIAGNOSIS:'):
                diagnosis = part.replace('DIAGNOSIS:\n', '')
            elif part.startswith('PRESCRIPTION (Rx):'):
                medications = part.replace('PRESCRIPTION (Rx):\n', '')
            elif part.startswith('INSTRUCTIONS:'):
                instructions = part.replace('INSTRUCTIONS:\n', '')
            elif part.startswith('FOLLOW-UP:'):
                follow_up = part.replace('FOLLOW-UP:\n', '')
    
    return JsonResponse({
        'prescription': appointment.prescription,
        'chief_complaint': chief_complaint,
        'diagnosis': diagnosis,
        'medications': medications,
        'instructions': instructions,
        'follow_up': follow_up,
        'completion_status': appointment.completion_status
    })