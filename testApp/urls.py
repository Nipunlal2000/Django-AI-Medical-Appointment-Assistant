from django.urls import path
from . views import *
from rest_framework_simplejwt.views import TokenRefreshView

urlpatterns = [

    path('api/token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('books/',BookAPIView.as_view()),
    
    path('doctors/',DoctorAPIView.as_view()),
    
    path('availability/',DoctorAvailabilityAPIView.as_view()),
    
    path('availability-slots/',AvailabilitySlotAPIView.as_view()),
    
    path('patients/',PatientAPIView.as_view()),
        
    path('book-appointments/',BookAppointmentAPIView.as_view()),

]