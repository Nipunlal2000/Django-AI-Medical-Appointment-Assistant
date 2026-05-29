from datetime import timedelta

from rest_framework import serializers
from . models import *

class BookSerializer(serializers.ModelSerializer):
    class Meta:
        model = Book
        fields = '__all__'
    
    # field level validation    
    def validate_price(self,value):
        if value <= 0:
            raise serializers.ValidationError("Price must be greater than zero")
        return value
    
    # object level validation
    def validate(self,attrs):
        if not attrs.get('is_published') and attrs.get('price') > 1000:
            raise serializers.ValidationError("Unpublished books cannot be more than 1000")
        return attrs

class DoctorSerializer(serializers.ModelSerializer):
    class Meta:
        model = Doctor
        fields = '__all__'
        
    def create(self, validated_data):
        doctor = Doctor.objects.create(**validated_data)
        return doctor
    
class PatientSerializer(serializers.ModelSerializer):
    class Meta:
        model = Patient
        fields = '__all__'
    
    def create(self, validated_data):
        return Patient.objects.create(**validated_data)
    
class BookAppointmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = BookAppointment
        fields = '__all__'
        
    def create(self, validated_data):
        return BookAppointment.objects.create(**validated_data)


from datetime import datetime, timedelta

class DoctorAvailabilitySerializer(serializers.ModelSerializer):
    class Meta:
        model = DoctorAvailability
        fields = '__all__'
            
    def create(self, validated_data):
        start_time = validated_data.get('start_time')
        end_time = validated_data.get('end_time')
        slot_duration = validated_data.get('slot_duration')
        
        # Convert start_time and end_time to datetime objects
        start_time = datetime.combine(datetime.today().date(), start_time)
        end_time = datetime.combine(datetime.today().date(), end_time)
        
        # Calculate the number of slots
        num_slots = int((end_time - start_time).total_seconds() / (60 * slot_duration))
        
        # Create the DoctorAvailability object
        availability = DoctorAvailability.objects.create(**validated_data)
        
        # Create the DoctorAvailabilitySlot objects for each slot
        for i in range(num_slots):
            start_slot_time = start_time + timedelta(minutes=i * slot_duration)
            end_slot_time = start_time + timedelta(minutes=(i + 1) * slot_duration)
            DoctorAvailabilitySlot.objects.create(
                doctor_availability=availability,
                start_time=start_slot_time.time(),
                end_time=end_slot_time.time()
            )
        
        return availability

class DoctorAvailabilitySlotSerializer(serializers.ModelSerializer):
    doctor_name = serializers.ReadOnlyField(source='doctor_availability.doctor.name')

    class Meta:
        model = DoctorAvailabilitySlot
        fields = '__all__'
        depth = 1
        
    def create(self, validated_data):
        return DoctorAvailabilitySlot.objects.create(**validated_data)