"""
Service Center Appointment Booking Tools
"""
import pandas as pd
import os
from datetime import datetime, timedelta
from langchain_core.tools import tool
from typing import Optional

# Import email notification for automatic emails
try:
    from notification_tools import send_email_notification
    EMAIL_AVAILABLE = True
except ImportError:
    EMAIL_AVAILABLE = False

# File paths
APPOINTMENTS_FILE = 'Car-Warranty-System/data/appointments.csv'
SERVICE_CENTERS_FILE = 'Car-Warranty-System/data/service_centers.csv'
VEHICLES_FILE = 'Car-Warranty-System/data/customer_vehicles.csv'

def load_data(file_path):
    """Load CSV data with error handling"""
    if os.path.exists(file_path):
        return pd.read_csv(file_path)
    else:
        return pd.DataFrame()

def save_data(df, file_path):
    """Save data to CSV"""
    os.makedirs(os.path.dirname(file_path), exist_ok=True)
    df.to_csv(file_path, index=False)

def initialize_appointments_file():
    """Initialize appointments CSV if it doesn't exist"""
    if not os.path.exists(APPOINTMENTS_FILE):
        appointments_df = pd.DataFrame(columns=[
            'appointment_id', 'vehicle_registration', 'service_center', 'appointment_date',
            'appointment_time', 'service_type', 'status', 'customer_name', 'customer_phone',
            'customer_email', 'notes', 'created_at'
        ])
        save_data(appointments_df, APPOINTMENTS_FILE)


@tool
def check_service_center_availability(
    service_center_name: str,
    preferred_date: str,
    service_type: str = "warranty_service"
) -> dict:
    """
    Check available appointment slots at a service center for a specific date.
    
    Args:
        service_center_name (str): Name of the service center
        preferred_date (str): Date to check availability (dd/mm/YYYY format)
        service_type (str): Type of service (warranty_service, ccp_claim, general_service)
    
    Returns:
        dict: Available time slots and booking information
        
    Examples:
        - Check slots for warranty inspection
        - Check slots for CCP claim inspection
        - Check slots for general service
    """
    try:
        initialize_appointments_file()
        appointments_df = load_data(APPOINTMENTS_FILE)
        service_centers_df = load_data(SERVICE_CENTERS_FILE)
        
        # Verify service center exists
        center = service_centers_df[service_centers_df['center_name'].str.contains(service_center_name, case=False, na=False)]
        if center.empty:
            return {"error": f"Service center '{service_center_name}' not found"}
        
        center_info = center.iloc[0]
        
        # Parse date
        try:
            check_date = datetime.strptime(preferred_date, '%d/%m/%Y')
        except:
            return {"error": "Invalid date format. Use dd/mm/YYYY"}
        
        # Check if date is in the past
        if check_date.date() < datetime.now().date():
            return {"error": "Cannot book appointments for past dates"}
        
        # Get existing appointments for this center and date
        existing_appointments = appointments_df[
            (appointments_df['service_center'] == center_info['center_name']) &
            (appointments_df['appointment_date'] == preferred_date) &
            (appointments_df['status'].isin(['confirmed', 'pending']))
        ]
        
        # Define available time slots (9 AM to 6 PM, 1-hour slots)
        all_slots = [
            "09:00 AM", "10:00 AM", "11:00 AM", "12:00 PM",
            "02:00 PM", "03:00 PM", "04:00 PM", "05:00 PM"
        ]
        
        # Get booked slots
        booked_slots = existing_appointments['appointment_time'].tolist() if not existing_appointments.empty else []
        
        # Calculate available slots
        available_slots = [slot for slot in all_slots if slot not in booked_slots]
        
        return {
            "service_center": center_info['center_name'],
            "city": center_info['city'],
            "address": center_info['address'],
            "phone": center_info['phone'],
            "date": preferred_date,
            "day_of_week": check_date.strftime('%A'),
            "available_slots": available_slots,
            "total_available": len(available_slots),
            "booked_slots": len(booked_slots),
            "service_type": service_type,
            "message": f"{len(available_slots)} slots available on {preferred_date}"
        }
        
    except Exception as e:
        return {"error": f"Error checking availability: {str(e)}"}


@tool
def book_service_appointment(
    vehicle_registration: str,
    service_center_name: str,
    appointment_date: str,
    appointment_time: str,
    service_type: str,
    customer_phone: Optional[str] = None,
    customer_email: Optional[str] = None,
    notes: Optional[str] = ""
) -> dict:
    """
    Book an appointment at a service center for warranty or claim services.
    Email and phone will be auto-detected from user profile if not provided.
    
    Args:
        vehicle_registration (str): Vehicle registration number
        service_center_name (str): Name of the service center
        appointment_date (str): Appointment date (dd/mm/YYYY)
        appointment_time (str): Appointment time (e.g., "10:00 AM")
        service_type (str): Type of service (warranty_inspection, ccp_claim_inspection, general_service)
        customer_phone (str, optional): Customer phone (auto-detected from profile if not provided)
        customer_email (str, optional): Customer email (auto-detected from profile if not provided)
        notes (str, optional): Additional notes or requirements
    
    Returns:
        dict: Booking confirmation with appointment ID
        
    Examples:
        - Book warranty inspection appointment
        - Book CCP claim damage assessment
        - Book general service appointment
    """
    try:
        initialize_appointments_file()
        appointments_df = load_data(APPOINTMENTS_FILE)
        vehicles_df = load_data(VEHICLES_FILE)
        service_centers_df = load_data(SERVICE_CENTERS_FILE)
        
        # Verify vehicle exists
        vehicle = vehicles_df[vehicles_df['registration'] == vehicle_registration]
        if vehicle.empty:
            return {"error": f"Vehicle {vehicle_registration} not found"}
        
        vehicle_info = vehicle.iloc[0]
        
        # Auto-detect user email and phone from profile if not provided
        if not customer_email or not customer_phone:
            # Load user data
            users_df = load_data('Car-Warranty-System/data/users.csv')
            user_id_file = 'Car-Warranty-System/data/user_id.conf'
            
            if os.path.exists(user_id_file):
                with open(user_id_file, 'r') as f:
                    current_user_id = int(f.read().strip())
                    user_record = users_df[users_df['user_id'] == current_user_id]
                    
                    if not user_record.empty:
                        if not customer_email:
                            customer_email = user_record.iloc[0]['email']
                        if not customer_phone:
                            customer_phone = user_record.iloc[0]['phone']
        
        # Verify service center exists
        center = service_centers_df[service_centers_df['center_name'].str.contains(service_center_name, case=False, na=False)]
        if center.empty:
            return {"error": f"Service center '{service_center_name}' not found"}
        
        center_info = center.iloc[0]
        
        # Check if slot is available
        existing_booking = appointments_df[
            (appointments_df['service_center'] == center_info['center_name']) &
            (appointments_df['appointment_date'] == appointment_date) &
            (appointments_df['appointment_time'] == appointment_time) &
            (appointments_df['status'].isin(['confirmed', 'pending']))
        ]
        
        if not existing_booking.empty:
            return {"error": f"Time slot {appointment_time} on {appointment_date} is already booked"}
        
        # Generate appointment ID
        new_appointment_id = appointments_df['appointment_id'].max() + 1 if not appointments_df.empty else 1
        
        # Create appointment record
        new_appointment = {
            'appointment_id': new_appointment_id,
            'vehicle_registration': vehicle_registration,
            'service_center': center_info['center_name'],
            'appointment_date': appointment_date,
            'appointment_time': appointment_time,
            'service_type': service_type,
            'status': 'confirmed',
            'customer_name': vehicle_info.get('customer_id', 'Customer'),
            'customer_phone': customer_phone,
            'customer_email': customer_email,
            'notes': notes,
            'created_at': datetime.now().strftime('%d/%m/%Y %H:%M:%S')
        }
        
        # Add to dataframe
        new_appointment_df = pd.DataFrame([new_appointment])
        appointments_df = pd.concat([appointments_df, new_appointment_df], ignore_index=True)
        save_data(appointments_df, APPOINTMENTS_FILE)
        
        # Prepare response
        response = {
            "success": True,
            "appointment_id": new_appointment_id,
            "confirmation_number": f"MSAP{new_appointment_id:06d}",
            "vehicle_registration": vehicle_registration,
            "vehicle_model": vehicle_info['model'],
            "service_center": center_info['center_name'],
            "service_center_address": center_info['address'],
            "service_center_phone": center_info['phone'],
            "appointment_date": appointment_date,
            "appointment_time": appointment_time,
            "service_type": service_type.replace('_', ' ').title(),
            "status": "Confirmed",
            "message": "Appointment booked successfully!",
            "confirmation_sent_to": customer_email if customer_email else "Email not available",
            "instructions": [
                "Confirmation email sent to your registered email",
                f"Arrive 15 minutes before your appointment at {appointment_time}",
                "Bring your vehicle registration documents",
                "Bring warranty/CCP documents if applicable",
                f"Contact service center at {center_info['phone']} if you need to reschedule"
            ]
        }
        
        # AUTOMATICALLY SEND CONFIRMATION EMAIL
        if EMAIL_AVAILABLE and customer_email:
            try:
                email_message = f"""
                Your appointment has been confirmed!
                
                Confirmation Number: MSAP{new_appointment_id:06d}
                
                Vehicle: {vehicle_registration} ({vehicle_info['model']})
                Service Center: {center_info['center_name']}
                Address: {center_info['address']}
                Phone: {center_info['phone']}
                
                Date: {appointment_date}
                Time: {appointment_time}
                Service Type: {service_type.replace('_', ' ').title()}
                
                Important Instructions:
                - Arrive 15 minutes before your appointment
                - Bring your vehicle registration documents
                - Bring warranty/CCP documents if applicable
                
                If you need to reschedule, contact us at {center_info['phone']}
                
                Thank you for choosing Car Warranty Services!
                """
                
                email_result = send_email_notification(
                    recipient_email=customer_email,
                    subject=f"Appointment Confirmed - {appointment_date} at {appointment_time}",
                    message=email_message,
                    notification_type="general"
                )
                
                if email_result.get("success", False):
                    response["email_confirmation"] = f"Confirmation email sent to {customer_email}"
                else:
                    response["email_confirmation"] = "Appointment confirmed, but email notification could not be sent"
                
            except Exception as email_error:
                # Don't fail the booking if email fails
                response["email_confirmation"] = "Appointment confirmed, but email notification failed"
        else:
            response["email_confirmation"] = "Email not sent (no email address found in your profile)"
        
        return response
        
    except Exception as e:
        return {"error": f"Booking failed: {str(e)}"}


@tool
def view_my_appointments(customer_phone: str) -> dict:
    """
    View all appointments booked by a customer.
    
    Args:
        customer_phone (str): Customer's phone number
    
    Returns:
        dict: List of all customer appointments with status
    """
    try:
        initialize_appointments_file()
        appointments_df = load_data(APPOINTMENTS_FILE)
        
        customer_appointments = appointments_df[appointments_df['customer_phone'] == customer_phone]
        
        if customer_appointments.empty:
            return {
                "message": "No appointments found",
                "total_appointments": 0
            }
        
        # Sort by date (most recent first)
        customer_appointments = customer_appointments.sort_values('created_at', ascending=False)
        
        return {
            "appointments": customer_appointments.to_dict(orient='records'),
            "total_appointments": len(customer_appointments)
        }
        
    except Exception as e:
        return {"error": f"Error retrieving appointments: {str(e)}"}


@tool
def cancel_appointment(appointment_id: int, cancellation_reason: str = "") -> dict:
    """
    Cancel a service center appointment.
    
    Args:
        appointment_id (int): ID of the appointment to cancel
        cancellation_reason (str, optional): Reason for cancellation
    
    Returns:
        dict: Cancellation confirmation
    """
    try:
        initialize_appointments_file()
        appointments_df = load_data(APPOINTMENTS_FILE)
        
        if appointment_id not in appointments_df['appointment_id'].values:
            return {"error": f"Appointment ID {appointment_id} not found"}
        
        appointment = appointments_df[appointments_df['appointment_id'] == appointment_id].iloc[0]
        
        if appointment['status'] == 'cancelled':
            return {"error": "Appointment is already cancelled"}
        
        if appointment['status'] == 'completed':
            return {"error": "Cannot cancel a completed appointment"}
        
        # Update status
        appointments_df.loc[appointments_df['appointment_id'] == appointment_id, 'status'] = 'cancelled'
        save_data(appointments_df, APPOINTMENTS_FILE)
        
        return {
            "success": True,
            "appointment_id": appointment_id,
            "confirmation_number": f"MSAP{appointment_id:06d}",
            "vehicle_registration": appointment['vehicle_registration'],
            "appointment_date": appointment['appointment_date'],
            "appointment_time": appointment['appointment_time'],
            "service_center": appointment['service_center'],
            "cancellation_reason": cancellation_reason,
            "message": "Appointment cancelled successfully",
            "note": "You can book a new appointment anytime"
        }
        
    except Exception as e:
        return {"error": f"Cancellation failed: {str(e)}"}


@tool
def reschedule_appointment(
    appointment_id: int,
    new_date: str,
    new_time: str
) -> dict:
    """
    Reschedule an existing appointment to a new date and time.
    
    Args:
        appointment_id (int): ID of the appointment to reschedule
        new_date (str): New appointment date (dd/mm/YYYY)
        new_time (str): New appointment time (e.g., "02:00 PM")
    
    Returns:
        dict: Rescheduling confirmation
    """
    try:
        initialize_appointments_file()
        appointments_df = load_data(APPOINTMENTS_FILE)
        
        if appointment_id not in appointments_df['appointment_id'].values:
            return {"error": f"Appointment ID {appointment_id} not found"}
        
        appointment = appointments_df[appointments_df['appointment_id'] == appointment_id].iloc[0]
        
        if appointment['status'] == 'cancelled':
            return {"error": "Cannot reschedule a cancelled appointment"}
        
        if appointment['status'] == 'completed':
            return {"error": "Cannot reschedule a completed appointment"}
        
        # Check if new slot is available
        service_center = appointment['service_center']
        existing_booking = appointments_df[
            (appointments_df['service_center'] == service_center) &
            (appointments_df['appointment_date'] == new_date) &
            (appointments_df['appointment_time'] == new_time) &
            (appointments_df['appointment_id'] != appointment_id) &
            (appointments_df['status'].isin(['confirmed', 'pending']))
        ]
        
        if not existing_booking.empty:
            return {"error": f"Time slot {new_time} on {new_date} is already booked"}
        
        # Update appointment
        old_date = appointment['appointment_date']
        old_time = appointment['appointment_time']
        
        appointments_df.loc[appointments_df['appointment_id'] == appointment_id, 'appointment_date'] = new_date
        appointments_df.loc[appointments_df['appointment_id'] == appointment_id, 'appointment_time'] = new_time
        save_data(appointments_df, APPOINTMENTS_FILE)
        
        return {
            "success": True,
            "appointment_id": appointment_id,
            "confirmation_number": f"MSAP{appointment_id:06d}",
            "vehicle_registration": appointment['vehicle_registration'],
            "service_center": service_center,
            "old_date": old_date,
            "old_time": old_time,
            "new_date": new_date,
            "new_time": new_time,
            "message": "Appointment rescheduled successfully!"
        }
        
    except Exception as e:
        return {"error": f"Rescheduling failed: {str(e)}"}
