from rest_framework.views import APIView

from testApp.models import *
from testApp.serializers import *
from .mixins import *

# class BookAPIView(APIView):
#     def get(self,request):
#         books = Book.objects.all()
        
#         data = []
#         for book in books:
#             data.append({
#                 "id":book.id,
#                 "title":book.title,
#                 "author":book.author,
#                 "price": str(book.price),
#                 "is_published":book.is_published 
#             })
#         return custom200("Get rquest recieved",data)
    
#     def post(self, request):
#         data = request.data
        
#         book = Book.objects.create(
#             title=data.get('title'),
#             author=data.get('author'),
#             price=data.get('price'),
#             is_published = data.get('is_published',True)
#         )
#         return custom201("Post request recieved",book.id)


class BookAPIView(APIView):
    def get(self,request):
        books = Book.objects.all()
        serializer = BookSerializer(books, many=True) # serialize
        return custom200("Books fetched successfully",serializer.data)
    
    def post(self, request):
        serializer = BookSerializer(data=request.data) # deserialize
        
        if serializer.is_valid():
            serializer.save()
            return custom201("Book created successfully",serializer.data)
        return custom400("Failed to create book",serializer.errors)    
    
from django.http import JsonResponse
from django.contrib.auth.models import User

def internal_user_count(request):
    """Secure endpoint used by the sidecar server to check DB stats."""
    count = User.objects.count()
    return JsonResponse({"count": count})


class DoctorAPIView(APIView):
    
    def get(self, request):
        doctors = Doctor.objects.all()
        serializer = DoctorSerializer(doctors, many=True)
        return custom200("Doctors fetched successfully",serializer.data)
    
    def post(self, request):
        data = request.data
        serializer = DoctorSerializer(data=data)
        if serializer.is_valid():
            doctor = serializer.save()
        else:
            return custom400("Failed to create doctor",serializer.errors)

        return custom201("Doctor created successfully",serializer.data)
    

class PatientAPIView(APIView):
    
    def get(self, request):
        patients = Patient.objects.all()
        serializer = PatientSerializer(patients, many=True)
        return custom200("Patients fetched successfully",serializer.data)
    
    def post(self, request):
        data = request.data
        serializer = PatientSerializer(data=data)
        if serializer.is_valid():
            patient = serializer.save()
        else:
            return custom400("Failed to create patient",serializer.errors)

        return custom201("Patient created successfully",serializer.data)
    

class BookAppointmentAPIView(APIView):
    
    def get(self, request):
        appointments = BookAppointment.objects.all()
        serializer = BookAppointmentSerializer(appointments, many=True)
        return custom200("Appointments fetched successfully",serializer.data)
    
    def post(self, request):
        data = request.data
        serializer = BookAppointmentSerializer(data=data)
        if serializer.is_valid():
            appointment = serializer.save()
        else:
            return custom400("Failed to create appointment",serializer.errors)

        return custom201("Appointment created successfully",serializer.data)

class DoctorAvailabilityAPIView(APIView):
    
    def get(self, request):
        availabilities = DoctorAvailability.objects.all()
        serializer = DoctorAvailabilitySerializer(availabilities, many=True)
        return custom200("Availabilities fetched successfully",serializer.data)
    
    def post(self, request):
        data = request.data
        serializer = DoctorAvailabilitySerializer(data=data)
        if serializer.is_valid():
            availability = serializer.save()
        else:
            return custom400("Failed to create availability",serializer.errors)

        return custom201("Availability created successfully",serializer.data)
    
class AvailabilitySlotAPIView(APIView):
    
    def get(self, request):
        slots = DoctorAvailabilitySlot.objects.all()
        serializer = DoctorAvailabilitySlotSerializer(slots, many=True)
        return custom200("Slots fetched successfully",serializer.data)
    
    def post(self, request):
        data = request.data
        serializer = DoctorAvailabilitySlotSerializer(data=data)
        if serializer.is_valid():
            slot = serializer.save()
        else:
            return custom400("Failed to create slot",serializer.errors)

        return custom201("Slot created successfully",serializer.data)