from django.urls import path
from . import views

urlpatterns = [
    path('', views.home, name='home'),

    path('services/', views.services, name='services'),
    path('login/', views.login_view, name='login'),
    path('signup/', views.signup_view, name='signup'),
    path('prevcare/', views.prevcare, name='prevcare'),
    path('surg/', views.surg, name='surg'),
    path('dent/', views.dent, name='dent'),
    path('diag/', views.diag, name='diag'),
    path('emer/', views.emer, name='emer'),
    path('nutri/', views.nutri, name='nutri'),
    path('logout/', views.logout_view, name='logout'),
    path('profile/', views.profile_view, name='profile'),
    path('appt/', views.appointment_view, name='appt'),
    path('ourteam/', views.our_team_view, name='ourteam'),
    path('receipt/<str:appointment_id>/', views.receipt_view, name='receipt'),
    path('doctor-dashboard/', views.doctor_dashboard, name='doctor_dashboard'),
    path('doctor/save-prescription/<str:appointment_id>/', views.save_prescription, name='save_prescription'),
    path('doctor/prescription-data/<str:appointment_id>/', views.get_prescription_data, name='get_prescription_data'),
    path('prescription-pdf/<str:appointment_id>/', views.prescription_pdf_view, name='prescription_pdf'),
    path('doctor/get-existing-prescription/<str:appointment_id>/', views.get_existing_prescription, name='get_existing_prescription'),
    path('prescription-pdf/<str:appointment_id>/', views.prescription_pdf_view, name='prescription_pdf'),
    path('receipt/<str:appointment_id>/', views.receipt_view, name='receipt'),
]

