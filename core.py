from conf import *
from datetime import date, datetime, timedelta
from langchain_core.messages.human import HumanMessage
from langchain_core.messages.ai import AIMessage
from dateutil.parser import parse, ParserError
from dotenv import load_dotenv
import os

# Load environment variables from .env file (for email SMTP configuration)
load_dotenv()
from typing import Optional, Tuple, Dict, List, Any
import pandas as pd
from langchain_core.messages import ToolMessage
from langchain_core.runnables import RunnableLambda
from langchain_core.tools import tool
from langgraph.prebuilt import ToolNode
from typing import Annotated
from typing_extensions import TypedDict
from langgraph.graph.message import AnyMessage, add_messages
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, StateGraph, START
from langgraph.prebuilt import tools_condition
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import Runnable, RunnableConfig
from fuzzywuzzy import process, fuzz

# Import free agentic capabilities (CSV-based, no external APIs needed)
from appointment_tools import (
    check_service_center_availability,
    book_service_appointment,
    view_my_appointments,
    cancel_appointment,
    reschedule_appointment
)

# Import email notification tool
from notification_tools import send_email_notification

def load_data(file_path):
    if os.path.exists(file_path):
        return pd.read_csv(file_path)
    else:
        return pd.DataFrame()


def save_data(df, file_path):
    df.to_csv(file_path, index=False)


vehicles_df = load_data(VEHICLES_FILE_PATH)
warranties_df = load_data(WARRANTIES_FILE_PATH)
customers_df = load_data(CUSTOMERS_FILE_PATH)
ccp_packages_df = load_data(CCP_PACKAGES_FILE_PATH)
claims_df = load_data(CLAIMS_FILE_PATH)
service_centers_df = load_data(SERVICE_CENTERS_FILE_PATH)

with open('Car-Warranty-System/data/user_id.conf', 'r') as file:
    user_id = int(file.read().strip())
user_info = customers_df[customers_df['user_id'] == int(user_id)]




@tool
def lookup_policy(query: str) -> str:
    """Consult the Car warranty and CCP policies to check whether certain options are permitted.
    Use this before processing warranty purchases or claims."""
    docs = retriever.query(query, k=2)
    return "\n\n".join([doc["page_content"] for doc in docs])


@tool
def calculator(operation: str, num1: float, num2: float) -> dict:
    """

    This tool performs basic arithmetic calculations to help with price calculations and other numerical tasks related to warranty services.

    **Purpose:**
    The `calculator` function assists in performing simple arithmetic operations, useful for calculating warranty costs, applying discounts, or determining total charges.

    **Arguments:**
    - `operation` (str): Specifies the type of arithmetic operation. Valid options:
        - 'add': Add two numbers (e.g., warranty price + additional fees)
        - 'subtract': Subtract one number from another (e.g., price after discount)
        - 'multiply': Multiply two numbers (e.g., package price calculations)
        - 'divide': Divide one number by another (e.g., average cost calculations)
    - `num1` (float): First number in the calculation (e.g., warranty price, discount amount)
    - `num2` (float): Second number in the calculation (e.g., additional charges, divisor)

    **Returns:**
    - Dictionary with either:
        - `'result'`: Calculation result as float or integer
        - `'error'`: Error message for invalid operations or division by zero

    **Examples:**
    - **Adding Warranty Costs:**
      ```python
      calculator('add', 15000.0, 7500.0)
      # Returns: {'result': 22500.0}
      ```

    - **Calculating Discounted Price:**
      ```python
      calculator('subtract', 15000.0, 2000.0)
      # Returns: {'result': 13000.0}
      ```

    - **Package Cost Calculation:**
      ```python
      calculator('multiply', 3500.0, 2)
      # Returns: {'result': 7000.0}
      ```

    - **Average Cost Per Year:**
      ```python
      calculator('divide', 15000.0, 3)
      # Returns: {'result': 5000.0}
      ```

    **Error Handling:**
    Returns error message for invalid operations or division by zero.

    Use this tool for warranty service price calculations.

    """

    # Ensure the operation is valid
    valid_operations = ['add', 'subtract', 'multiply', 'divide']
    if operation not in valid_operations:
        return {"error": f"Invalid operation '{operation}'. Valid operations are {', '.join(valid_operations)}."}

    # Perform the calculation based on the operation
    try:
        if operation == 'add':
            result = num1 + num2
        elif operation == 'subtract':
            result = num1 - num2
        elif operation == 'multiply':
            result = num1 * num2
        elif operation == 'divide':
            if num2 == 0:
                return {"error": "Division by zero is not allowed."}
            result = num1 / num2
        return {"result": result}

    except Exception as e:
        return {"error": str(e)}



@tool
def dates_calculator(operation: str, start_date: str, end_date: Optional[str] = None, days: Optional[int] = None) -> Dict[str, any]:
    """
    This tool performs date calculations to help manage warranty periods and other date-related tasks.

    **Purpose:**
    The `dates_calculator` function assists with various date calculations, such as finding the duration between two dates, calculating future or past dates, or determining days between dates. This is useful for warranty eligibility windows, validity periods, and deadline tracking.

    **Arguments:**
    - `operation` (str): Specifies the type of date calculation to perform. The valid options are:
        - 'duration': Calculate the number of days between the start date and today.
        - 'add_days': Calculate a future date by adding a specified number of days to the start date.
        - 'subtract_days': Calculate a past date by subtracting a specified number of days from the start date.
        - 'days_between': Calculate the number of days between two given dates.
    - `start_date` (str): The initial date in `dd/mm/YYYY` format. This is the reference date for the calculation.
    - `end_date` (str, optional): The end date in `dd/mm/YYYY` format. This argument is required for the 'days_between' operation.
    - `days` (int, optional): The number of days to add or subtract from the start date. This argument is required for 'add_days' and 'subtract_days' operations.

    **Returns:**
    - A dictionary containing either:
        - `'result'`: The result of the date calculation. For 'duration' and 'days_between', it returns the number of days. For 'add_days' and 'subtract_days', it returns the calculated date in `dd/mm/YYYY` format.
        - `'error'`: A message indicating any issues with the operation or input values (e.g., invalid operation type or missing arguments).

    **Examples:**
    - **Calculating Duration Between Dates:**
      ```python
      dates_calculator('duration', '01/01/2024')
      # Returns: {'result': 45}
      ```
      Calculates the number of days from January 1, 2024, to today.

    - **Finding a Future Date:**
      ```python
      dates_calculator('add_days', '01/01/2024', days=30)
      # Returns: {'result': '31/01/2024'}
      ```
      Calculates the date 30 days after January 1, 2024.

    - **Finding a Past Date:**
      ```python
      dates_calculator('subtract_days', '01/01/2024', days=30)
      # Returns: {'result': '02/12/2023'}
      ```
      Calculates the date 30 days before January 1, 2024.

    - **Calculating Days Between Two Dates:**
      ```python
      dates_calculator('days_between', '01/01/2024', '15/02/2024')
      # Returns: {'result': 45}
      ```
      Calculates the number of days between January 1, 2024, and February 15, 2024.

    **Error Handling:**
    - If you attempt an invalid operation or provide an incorrect date format, the function will return an error message to help you understand what went wrong.
    - If the 'add_days' or 'subtract_days' operation is selected but no days argument is provided, it will also return an error message.
    - If the 'days_between' operation is selected but no end_date argument is provided, it will return an error message.

    Use this tool to efficiently handle date calculations related to warranty periods, eligibility windows, or any other date-related needs.
    """

    try:
        # Parse the start date
        start_date = datetime.strptime(start_date, '%d/%m/%Y')

        if operation == 'duration':
            # Calculate the duration between the start date and today
            today = datetime.now()
            duration = (today - start_date).days
            return {"result": duration}

        elif operation == 'add_days':
            if days is None:
                return {"error": "The 'days' argument is required for 'add_days' operation."}
            # Calculate the future date
            future_date = start_date + timedelta(days=days)
            return {"result": future_date.strftime('%d/%m/%Y')}

        elif operation == 'subtract_days':
            if days is None:
                return {"error": "The 'days' argument is required for 'subtract_days' operation."}
            # Calculate the past date
            past_date = start_date - timedelta(days=days)
            return {"result": past_date.strftime('%d/%m/%Y')}

        elif operation == 'days_between':
            if end_date is None:
                return {"error": "The 'end_date' argument is required for 'days_between' operation."}
            # Parse the end date
            end_date = datetime.strptime(end_date, '%d/%m/%Y')
            # Calculate the number of days between the two dates
            days_between = (end_date - start_date).days
            return {"result": days_between}

        else:
            return {
                "error": f"Invalid operation '{operation}'. Valid operations are 'duration', 'add_days', 'subtract_days', and 'days_between'."}

    except ValueError as ve:
        return {"error": f"Date format error: {ve}"}
    except Exception as e:
        return {"error": str(e)}


@tool
def check_warranty_status(vehicle_registration: str) -> dict:
    """
    Check the current warranty and CCP status for a specific vehicle.

    Args:
        vehicle_registration (str): Vehicle registration number (e.g., 'MH02XX1234')

    Returns:
        dict: Current warranty status including standard warranty, extended warranty, and CCP status
    """
    vehicles_df = load_data(VEHICLES_FILE_PATH)
    warranties_df = load_data(WARRANTIES_FILE_PATH)
    
    try:
        vehicle = vehicles_df[vehicles_df['registration'] == vehicle_registration]
        if vehicle.empty:
            return {"error": f"Vehicle with registration {vehicle_registration} not found in our system."}
        
        vehicle_info = vehicle.iloc[0].to_dict()
        
        # Get active warranties
        active_warranties = warranties_df[
            (warranties_df['vehicle_registration'] == vehicle_registration) & 
            (warranties_df['status'] == 'active')
        ]
        
        result = {
            "vehicle_registration": vehicle_registration,
            "model": vehicle_info['model'],
            "purchase_date": vehicle_info['purchase_date'],
            "current_mileage": vehicle_info['current_mileage'],
            "standard_warranty_expiry": vehicle_info['warranty_expiry'],
            "has_extended_warranty": vehicle_info['has_extended_warranty'],
            "has_ccp": vehicle_info['has_ccp'],
            "active_warranties": active_warranties.to_dict(orient='records')
        }
        
        return result
        
    except Exception as e:
        return {"error": f"An error occurred while checking warranty status: {str(e)}"}



@tool
def check_ccp_eligibility(vehicle_registration: str) -> dict:
    """
    Check eligibility for Customer Convenience Package (CCP) for a specific vehicle.
    
    Prerequisites for CCP:
    - Vehicle must have Extended Warranty
    - Must be within 1 year 9 months (21 months) of vehicle purchase date
    - Mileage within package limits
    
    Args:
        vehicle_registration (str): Vehicle registration number (e.g., 'MH02XX1234')
    
    Returns:
        dict: Eligibility status and available CCP packages with prices and purchase deadline
    """
    vehicles_df = load_data(VEHICLES_FILE_PATH)
    ccp_packages_df = load_data(CCP_PACKAGES_FILE_PATH)
    
    try:
        vehicle = vehicles_df[vehicles_df['registration'] == vehicle_registration]
        if vehicle.empty:
            return {"error": f"Vehicle with registration {vehicle_registration} not found."}
        
        vehicle_info = vehicle.iloc[0].to_dict()
        
        # Check if vehicle has extended warranty
        if not vehicle_info['has_extended_warranty']:
            return {
                "eligible": False,
                "reason": "Extended Warranty is required before purchasing CCP. Please purchase Extended Warranty first.",
                "vehicle_registration": vehicle_registration,
                "model": vehicle_info['model']
            }
        
        # Check if already has CCP
        if vehicle_info['has_ccp']:
            return {
                "eligible": False,
                "reason": "Vehicle already has an active CCP package.",
                "vehicle_registration": vehicle_registration,
                "model": vehicle_info['model']
            }
        
        # Calculate eligibility window (within 21 months of purchase)
        purchase_date = datetime.strptime(vehicle_info['purchase_date'], '%d/%m/%Y')
        eligibility_end_date = purchase_date + timedelta(days=21*30)  # Approx 21 months
        current_date = datetime.now()
        
        if current_date > eligibility_end_date:
            return {
                "eligible": False,
                "reason": f"Purchase window expired. CCP must be purchased within 1 year 9 months of vehicle purchase date ({vehicle_info['purchase_date']}).",
                "vehicle_registration": vehicle_registration,
                "model": vehicle_info['model'],
                "purchase_deadline_was": eligibility_end_date.strftime('%d/%m/%Y')
            }
        
        # Vehicle is eligible - return available packages
        days_remaining = (eligibility_end_date - current_date).days
        current_mileage = vehicle_info['current_mileage']
        
        # Filter packages based on mileage
        available_packages = []
        for _, package in ccp_packages_df.iterrows():
            if current_mileage < package['max_kilometers']:
                available_packages.append({
                    "package_name": package['package_name'],
                    "duration": f"{package['duration_years']} Year{'s' if package['duration_years'] > 1 else ''}",
                    "coverage_km": f"Valid till {package['max_kilometers']:,} km",
                    "price": f"₹{package['price']:,}",
                    "price_value": package['price'],
                    "coverage": package['coverage_details']
                })
        
        return {
            "eligible": True,
            "vehicle_registration": vehicle_registration,
            "model": vehicle_info['model'],
            "purchase_date": vehicle_info['purchase_date'],
            "current_mileage": f"{current_mileage:,} km",
            "available_packages": available_packages,
            "purchase_deadline": eligibility_end_date.strftime('%d/%m/%Y'),
            "days_remaining": days_remaining
        }
        
    except Exception as e:
        return {"error": f"An error occurred while checking CCP eligibility: {str(e)}"}

@tool
def purchase_ccp_package(vehicle_registration: str, package_type: str, customer_email: str) -> dict:
    """
    Purchase a Customer Convenience Package (CCP) for a vehicle.
    First checks eligibility, then processes the purchase.

    Args:
        vehicle_registration (str): Vehicle registration number (e.g., 'MH02XX1234')
        package_type (str): Type of CCP package ('1year', '2year', or '3year')
        customer_email (str): Customer email for confirmation

    Returns:
        dict: Purchase confirmation with warranty ID and payment details
    """
    vehicles_df = load_data(VEHICLES_FILE_PATH)
    warranties_df = load_data(WARRANTIES_FILE_PATH)
    ccp_packages_df = load_data(CCP_PACKAGES_FILE_PATH)
    
    try:
        # Check eligibility first
        vehicle = vehicles_df[vehicles_df['registration'] == vehicle_registration]
        if vehicle.empty:
            return {"error": f"Vehicle with registration {vehicle_registration} not found."}
        
        vehicle_info = vehicle.iloc[0].to_dict()
        
        # Verify extended warranty
        if not vehicle_info['has_extended_warranty']:
            return {"error": "Extended Warranty is required before purchasing CCP."}
        
        # Verify not already having CCP
        if vehicle_info['has_ccp']:
            return {"error": "Vehicle already has an active CCP package."}
        
        # Get package details
        package_map = {'1year': 1, '2year': 2, '3year': 3}
        if package_type not in package_map:
            return {"error": "Invalid package type. Choose '1year', '2year', or '3year'."}
        
        package = ccp_packages_df[ccp_packages_df['duration_years'] == package_map[package_type]]
        if package.empty:
            return {"error": f"Package {package_type} not found."}
        
        package_info = package.iloc[0].to_dict()
        
        # Calculate dates
        warranty_start = datetime.strptime(vehicle_info['warranty_expiry'], '%d/%m/%Y')
        warranty_end = warranty_start + timedelta(days=package_info['duration_years']*365)
        
        # Create new warranty record
        new_warranty_id = warranties_df['warranty_id'].max() + 1 if not warranties_df.empty else 1
        new_warranty = {
            'warranty_id': new_warranty_id,
            'vehicle_registration': vehicle_registration,
            'warranty_type': 'ccp',
            'package_type': package_type,
            'start_date': warranty_start.strftime('%d/%m/%Y'),
            'end_date': warranty_end.strftime('%d/%m/%Y'),
            'status': 'pending_payment',
            'price': package_info['price'],
            'coverage_km': package_info['max_kilometers']
        }
        
        new_warranty_df = pd.DataFrame([new_warranty])
        warranties_df = pd.concat([warranties_df, new_warranty_df], ignore_index=True)
        save_data(warranties_df, WARRANTIES_FILE_PATH)
        
        # Update vehicle CCP status (will be activated after payment)
        vehicles_df.loc[vehicles_df['registration'] == vehicle_registration, 'has_ccp'] = True
        save_data(vehicles_df, VEHICLES_FILE_PATH)
        
        # Prepare response
        response = {
            "success": True,
            "warranty_id": new_warranty_id,
            "vehicle_registration": vehicle_registration,
            "model": vehicle_info['model'],
            "package": package_info['package_name'],
            "price": f"₹{package_info['price']:,}",
            "coverage_km": f"{package_info['max_kilometers']:,} km",
            "validity": f"{package_info['duration_years']} year(s)",
            "status": "Pending Payment",
            "payment_link": f"https://carwarranty.com/payment/{new_warranty_id}",
            "confirmation_email": customer_email,
            "message": "Please complete payment within 24 hours to activate your CCP package."
        }
        
        # AUTOMATICALLY SEND PURCHASE CONFIRMATION EMAIL
        if customer_email:
            try:
                email_message = f"""
                Your CCP purchase has been initiated!
                
                Warranty ID: {new_warranty_id}
                
                Vehicle: {vehicle_registration} ({vehicle_info['model']})
                Package: {package_info['package_name']}
                Price: ₹{package_info['price']:,}
                Coverage: Up to {package_info['max_kilometers']:,} km
                Validity: {package_info['duration_years']} year(s)
                
                Status: Pending Payment
                
                Payment Link: https://carwarranty.com/payment/{new_warranty_id}
                
                IMPORTANT: Please complete payment within 24 hours to activate your CCP package.
                
                What's Covered:
                - Engine damage from water entry (hydrolock)
                - Damage from adulterated fuel
                - Rodent damage to wiring
                - Insect damage to components
                
                Thank you for choosing Car Warranty Services!
                """
                
                email_result = send_email_notification(
                    recipient_email=customer_email,
                    subject=f"CCP Purchase Confirmation - Warranty ID {new_warranty_id}",
                    message=email_message,
                    notification_type="purchase_confirmation"
                )
                
                response["email_sent"] = email_result.get("success", False)
                response["email_status"] = email_result.get("message", "Email sending attempted")
                
            except Exception as email_error:
                response["email_sent"] = False
                response["email_status"] = f"Purchase confirmed but email failed: {str(email_error)}"
        else:
            response["email_sent"] = False
            response["email_status"] = "Email not sent (no email provided)"
        
        return response
        
    except Exception as e:
        return {"error": f"An error occurred during CCP purchase: {str(e)}"}



def is_warranty_active(warranty_id: int) -> bool:
    warranties_df = load_data(WARRANTIES_FILE_PATH)
    
    if warranty_id in warranties_df['warranty_id'].values:
        warranty_status = warranties_df.loc[warranties_df['warranty_id'] == warranty_id, 'status'].values[0]
        return warranty_status in ['active', 'pending_payment']
    
    return False


@tool
def cancel_warranty_service(warranty_id: int) -> dict:
    """
    Cancel a pending warranty or CCP service purchase.
    Only warranties with 'pending_payment' status can be cancelled.

    Args:
        warranty_id (int): ID of the warranty to be cancelled

    Returns:
        dict: Cancellation confirmation or error message
    """
    try:
        warranties_df = load_data(WARRANTIES_FILE_PATH)
        vehicles_df = load_data(VEHICLES_FILE_PATH)
        
        if warranty_id not in warranties_df['warranty_id'].values:
            return {"error": f"Warranty ID {warranty_id} not found."}
        
        warranty = warranties_df[warranties_df['warranty_id'] == warranty_id].iloc[0]
        
        if warranty['status'] == 'active':
            return {"error": "Active warranties cannot be cancelled. Please contact customer support."}
        
        if warranty['status'] != 'pending_payment':
            return {"error": f"Warranty with status '{warranty['status']}' cannot be cancelled."}
        
        # Cancel the warranty by setting status to 'cancelled'
        warranties_df.loc[warranties_df['warranty_id'] == warranty_id, 'status'] = 'cancelled'
        save_data(warranties_df, WARRANTIES_FILE_PATH)
        
        # Update vehicle CCP status if it was a CCP package
        if warranty['warranty_type'] == 'ccp':
            vehicles_df.loc[vehicles_df['registration'] == warranty['vehicle_registration'], 'has_ccp'] = False
            save_data(vehicles_df, VEHICLES_FILE_PATH)
        
        return {
            "success": True,
            "warranty_id": warranty_id,
            "vehicle_registration": warranty['vehicle_registration'],
            "warranty_type": warranty['warranty_type'],
            "message": f"{warranty['warranty_type'].upper()} warranty cancelled successfully. Refund will be processed within 7-10 business days."
        }
        
    except Exception as e:
        return {"error": f"An error occurred during cancellation: {str(e)}"}

@tool
def file_ccp_claim(vehicle_registration: str, claim_type: str, description: str, service_center: str = None) -> dict:
    """
    File a CCP claim for engine damage covered under the Customer Convenience Package.
    
    Valid claim types:
    - water_damage: Engine damage from water entry (hydrolock)
    - fuel_damage: Engine damage from adulterated fuel
    - rodent_damage: Wiring/component damage from rodents
    - insect_damage: Component damage from insects

    Args:
        vehicle_registration (str): Vehicle registration number
        claim_type (str): Type of claim (water_damage, fuel_damage, rodent_damage, insect_damage)
        description (str): Detailed description of the damage
        service_center (str, optional): Preferred service center name

    Returns:
        dict: Claim ID and next steps for processing
    """
    vehicles_df = load_data(VEHICLES_FILE_PATH)
    warranties_df = load_data(WARRANTIES_FILE_PATH)
    claims_df = load_data(CLAIMS_FILE_PATH)
    service_centers_df = load_data(SERVICE_CENTERS_FILE_PATH)
    
    try:
        # Verify vehicle exists
        vehicle = vehicles_df[vehicles_df['registration'] == vehicle_registration]
        if vehicle.empty:
            return {"error": f"Vehicle with registration {vehicle_registration} not found."}
        
        vehicle_info = vehicle.iloc[0].to_dict()
        
        # Verify vehicle has active CCP
        if not vehicle_info['has_ccp']:
            return {"error": "Vehicle does not have an active CCP package. Claims can only be filed with active CCP coverage."}
        
        # Check for active CCP warranty
        active_ccp = warranties_df[
            (warranties_df['vehicle_registration'] == vehicle_registration) & 
            (warranties_df['warranty_type'] == 'ccp') &
            (warranties_df['status'] == 'active')
        ]
        
        if active_ccp.empty:
            return {"error": "No active CCP warranty found for this vehicle."}
        
        # Validate claim type
        valid_claim_types = ['water_damage', 'fuel_damage', 'rodent_damage', 'insect_damage']
        if claim_type not in valid_claim_types:
            return {"error": f"Invalid claim type. Must be one of: {', '.join(valid_claim_types)}"}
        
        # Find nearest service center if not specified
        if not service_center:
            service_center = service_centers_df.iloc[0]['center_name']  # Default to first center
        
        # Create new claim
        new_claim_id = claims_df['claim_id'].max() + 1 if not claims_df.empty else 1
        filing_date = datetime.now().strftime('%d/%m/%Y')
        
        new_claim = {
            'claim_id': new_claim_id,
            'vehicle_registration': vehicle_registration,
            'claim_type': claim_type,
            'description': description,
            'filing_date': filing_date,
            'status': 'submitted',
            'service_center': service_center,
            'estimated_cost': 0,  # Will be updated by service center
            'resolution_date': ''
        }
        
        new_claim_df = pd.DataFrame([new_claim])
        claims_df = pd.concat([claims_df, new_claim_df], ignore_index=True)
        save_data(claims_df, CLAIMS_FILE_PATH)
        
        # Get logged-in user's email automatically
        global user_info
        customer_email = user_info.iloc[0]['email'] if not user_info.empty else None
        customer_name = user_info.iloc[0]['name'] if not user_info.empty else "Customer"
        
        # Prepare response
        response = {
            "success": True,
            "claim_id": new_claim_id,
            "claim_reference": f"CCP{new_claim_id:06d}",
            "vehicle_registration": vehicle_registration,
            "model": vehicle_info['model'],
            "claim_type": claim_type.replace('_', ' ').title(),
            "filing_date": filing_date,
            "status": "Submitted",
            "service_center": service_center,
            "next_steps": [
                "Claim submitted successfully",
                "Confirmation email sent to your registered email",
                "Vehicle inspection will be scheduled within 24-48 hours",
                "Service center will contact you for appointment",
                f"Claim reference number: CCP{new_claim_id:06d}",
                "Keep your vehicle registration and CCP documents ready"
            ],
            "estimated_processing_time": "5-7 business days",
            "confirmation_email_sent_to": customer_email if customer_email else "Email not available"
        }
        
        # AUTOMATICALLY SEND CLAIM CONFIRMATION EMAIL
        if customer_email:
            try:
                email_message = f"""
                Your CCP claim has been submitted successfully!
                
                Claim ID: {new_claim_id}
                Claim Reference: CCP{new_claim_id:06d}
                
                Vehicle: {vehicle_registration} ({vehicle_info['model']})
                Claim Type: {claim_type.replace('_', ' ').title()}
                Filing Date: {filing_date}
                Status: Submitted
                
                Service Center: {service_center}
                
                Next Steps:
                1. Claim submitted successfully
                2. Vehicle inspection will be scheduled within 24-48 hours
                3. Service center will contact you for appointment
                4. Keep your vehicle registration and CCP documents ready
                
                Estimated Processing Time: 5-7 business days
                
                You will receive updates via email as your claim progresses.
                
                Thank you for choosing Car Warranty Services!
                """
                
                email_result = send_email_notification(
                    recipient_email=customer_email,
                    subject=f"Claim Submitted - Reference: CCP{new_claim_id:06d}",
                    message=email_message,
                    notification_type="claim_update"
                )
                
                if email_result.get("success", False):
                    response["email_confirmation"] = f"Confirmation email sent to {customer_email}"
                else:
                    response["email_confirmation"] = f"Claim filed successfully, but email notification could not be sent"
                
            except Exception as email_error:
                response["email_confirmation"] = f"Claim filed successfully, but email notification failed"
        else:
            response["email_confirmation"] = "Email not sent (no email address found in your profile)"
        
        return response
        
    except Exception as e:
        return {"error": f"An error occurred while filing the claim: {str(e)}"}



@tool
def check_extended_warranty_eligibility(vehicle_registration: str) -> dict:
    """
    Check if a vehicle is eligible for Extended Warranty purchase.
    Extended Warranty can be purchased within the first 3 years of vehicle purchase.
    
    Args:
        vehicle_registration (str): Vehicle registration number
    
    Returns:
        dict: Eligibility status and available extended warranty options
    """
    vehicles_df = load_data(VEHICLES_FILE_PATH)
    
    try:
        vehicle = vehicles_df[vehicles_df['registration'] == vehicle_registration]
        if vehicle.empty:
            return {"error": f"Vehicle with registration {vehicle_registration} not found."}
        
        vehicle_info = vehicle.iloc[0].to_dict()
        
        # Check if already has extended warranty
        if vehicle_info['has_extended_warranty']:
            return {
                "eligible": False,
                "reason": "Vehicle already has an Extended Warranty.",
                "vehicle_registration": vehicle_registration,
                "model": vehicle_info['model']
            }
        
        # Check if within purchase window (3 years from purchase)
        purchase_date = datetime.strptime(vehicle_info['purchase_date'], '%d/%m/%Y')
        eligibility_end = purchase_date + timedelta(days=3*365)
        current_date = datetime.now()
        
        if current_date > eligibility_end:
            return {
                "eligible": False,
                "reason": "Purchase window expired. Extended Warranty must be purchased within 3 years of vehicle purchase.",
                "vehicle_registration": vehicle_registration,
                "model": vehicle_info['model']
            }
        
        # Calculate remaining time
        days_remaining = (eligibility_end - current_date).days
        
        return {
            "eligible": True,
            "vehicle_registration": vehicle_registration,
            "model": vehicle_info['model'],
            "purchase_date": vehicle_info['purchase_date'],
            "current_mileage": f"{vehicle_info['current_mileage']:,} km",
            "standard_warranty_expiry": vehicle_info['warranty_expiry'],
            "available_options": [
                {
                    "option": "1 Year Extension",
                    "coverage": "Up to 120,000 km",
                    "price": "₹8,000"
                },
                {
                    "option": "2 Year Extension",
                    "coverage": "Up to 140,000 km",
                    "price": "₹12,000"
                },
                {
                    "option": "3 Year Extension",
                    "coverage": "Up to 160,000 km",
                    "price": "₹15,000"
                }
            ],
            "purchase_deadline": eligibility_end.strftime('%d/%m/%Y'),
            "days_remaining": days_remaining
        }
        
    except Exception as e:
        return {"error": f"An error occurred while checking eligibility: {str(e)}"}


@tool
def get_coverage_details(coverage_type: str) -> dict:
    """
    Get detailed information about what is covered under different warranty types.
    
    Args:
        coverage_type (str): Type of coverage ('extended_warranty' or 'ccp')
    
    Returns:
        dict: Detailed coverage information
    """
    if coverage_type.lower() == 'extended_warranty':
        return {
            "coverage_type": "Extended Warranty",
            "description": "Extends your standard 3-year warranty up to 6 years or 160,000 km",
            "what_is_covered": [
                "Manufacturing defects",
                "Mechanical failures (engine, transmission, drivetrain)",
                "Electrical and electronic component failures",
                "Steering system issues",
                "Brake system problems",
                "Cooling system failures",
                "Fuel system issues",
                "Air conditioning system"
            ],
            "what_is_not_covered": [
                "Regular maintenance and service",
                "Wear and tear items (brake pads, tires, batteries)",
                "Damage from accidents or misuse",
                "Modifications or alterations",
                "Cosmetic damage"
            ],
            "benefits": [
                "Peace of mind with extended protection",
                "Coverage at all authorized service centers",
                "Genuine parts replacement",
                "No additional paperwork for covered repairs"
            ]
        }
    elif coverage_type.lower() == 'ccp':
        return {
            "coverage_type": "Customer Convenience Package (CCP)",
            "description": "Special coverage for damage from water, fuel contamination, rodents, and insects",
            "prerequisite": "Extended Warranty must be active",
            "what_is_covered": [
                "Water Damage (Hydrolock): Engine damage from water entry during floods/waterlogging",
                "Fuel Damage: Engine and fuel system damage from adulterated or contaminated fuel",
                "Rodent Damage: Wiring harness and component damage caused by rodents",
                "Insect Damage: Damage to ECU and components caused by insect infestation"
            ],
            "coverage_limits": {
                "CCP 1 Year": "Valid till 25,000 km - ₹3,500",
                "CCP 2 Year": "Valid till 45,000 km - ₹5,500",
                "CCP 3 Year": "Valid till 60,000 km - ₹7,500"
            },
            "claim_process": [
                "Report incident immediately",
                "Visit authorized service center",
                "Submit CCP documents and vehicle registration",
                "Inspection within 24-48 hours",
                "Approval within 5-7 business days"
            ],
            "important_notes": [
                "Cannot be purchased without Extended Warranty",
                "Must be purchased within 1 year 9 months of vehicle purchase",
                "Valid only at Maruti Suzuki authorized service centers",
                "Covers repair/replacement costs as per policy terms"
            ]
        }
    else:
        return {"error": "Invalid coverage type. Use 'extended_warranty' or 'ccp'."}


@tool
def find_service_center(city: str = None, vehicle_registration: str = None) -> dict:
    """
    Find nearest authorized service centers.
    
    Args:
        city (str, optional): City name to search service centers
        vehicle_registration (str, optional): Vehicle registration to find nearest center
    
    Returns:
        dict: List of service centers with contact details
    """
    service_centers_df = load_data(SERVICE_CENTERS_FILE_PATH)
    
    try:
        if city:
            # Search by city
            centers = service_centers_df[service_centers_df['city'].str.contains(city, case=False, na=False)]
            if centers.empty:
                return {"error": f"No service centers found in {city}. Please try another city."}
        else:
            # Return all centers or top 5
            centers = service_centers_df.head(10)
        
        result_centers = []
        for _, center in centers.iterrows():
            result_centers.append({
                "center_name": center['center_name'],
                "city": center['city'],
                "address": center['address'],
                "phone": center['phone'],
                "email": center['email']
            })
        
        return {
            "service_centers": result_centers,
            "total_found": len(result_centers),
            "note": "All centers are authorized for Extended Warranty and CCP services"
        }
        
    except Exception as e:
        return {"error": f"An error occurred while searching service centers: {str(e)}"}


@tool
def show_my_warranties() -> dict:
    """
    Retrieve all warranties (Extended Warranty and CCP) for the current user's vehicles.

    Returns:
        dict: Dictionary of all warranties associated with user's vehicles
    """
    global user_id
    vehicles_df = load_data(VEHICLES_FILE_PATH)
    warranties_df = load_data(WARRANTIES_FILE_PATH)
    
    # Get user's vehicles
    user_vehicles = vehicles_df[vehicles_df['customer_id'] == user_id]
    
    if user_vehicles.empty:
        return {"message": "No vehicles registered under your account."}
    
    # Get all warranties for user's vehicles
    user_vehicle_regs = user_vehicles['registration'].tolist()
    user_warranties = warranties_df[warranties_df['vehicle_registration'].isin(user_vehicle_regs)]
    
    # Merge with vehicle info
    result = pd.merge(user_warranties, user_vehicles[['registration', 'model']], 
                     left_on='vehicle_registration', right_on='registration', how='left')
    
    return {
        "warranties": result.to_dict(orient='records'),
        "total_warranties": len(result)
    }


@tool
def show_my_claims() -> dict:
    """
    Retrieve all CCP claims filed by the user for their vehicles.

    Returns:
        dict: Dictionary of all claims with their current status
    """
    global user_id
    vehicles_df = load_data(VEHICLES_FILE_PATH)
    claims_df = load_data(CLAIMS_FILE_PATH)
    
    # Get user's vehicles
    user_vehicles = vehicles_df[vehicles_df['customer_id'] == user_id]
    
    if user_vehicles.empty:
        return {"message": "No vehicles registered under your account."}
    
    # Get all claims for user's vehicles
    user_vehicle_regs = user_vehicles['registration'].tolist()
    user_claims = claims_df[claims_df['vehicle_registration'].isin(user_vehicle_regs)]
    
    # Merge with vehicle info
    result = pd.merge(user_claims, user_vehicles[['registration', 'model']], 
                     left_on='vehicle_registration', right_on='registration', how='left')
    
    return {
        "claims": result.to_dict(orient='records'),
        "total_claims": len(result)
    }


@tool
def show_my_vehicles() -> dict:
    """
    Retrieve all vehicles registered under the current user's account.

    Returns:
        dict: Dictionary containing all user's vehicles with warranty status
    """
    global user_id
    vehicles_df = load_data(VEHICLES_FILE_PATH)
    
    user_vehicles = vehicles_df[vehicles_df['customer_id'] == user_id]
    
    if user_vehicles.empty:
        return {"message": "No vehicles registered under your account."}
    
    return {
        "vehicles": user_vehicles.to_dict(orient='records'),
        "total_vehicles": len(user_vehicles)
    }


@tool
def show_customer_info() -> dict:
    """
    Retrieve personal information for the current user/customer.

    Returns:
        dict: Dictionary containing customer's personal information
    """
    global user_id
    customers_df = load_data(CUSTOMERS_FILE_PATH)
    return customers_df[customers_df['user_id'] == user_id].to_dict(orient='records')


@tool
def get_claim_status(claim_id: int) -> dict:
    """
    Get the current status and details of a specific CCP claim.

    Args:
        claim_id (int): ID of the claim to check

    Returns:
        dict: Detailed claim status and information
    """
    claims_df = load_data(CLAIMS_FILE_PATH)
    vehicles_df = load_data(VEHICLES_FILE_PATH)
    
    try:
        claim = claims_df[claims_df['claim_id'] == claim_id]
        if claim.empty:
            return {"error": f"Claim ID {claim_id} not found."}
        
        claim_info = claim.iloc[0].to_dict()
        
        # Get vehicle details
        vehicle = vehicles_df[vehicles_df['registration'] == claim_info['vehicle_registration']]
        vehicle_model = vehicle.iloc[0]['model'] if not vehicle.empty else "Unknown"
        
        status_messages = {
            "submitted": "Claim submitted. Awaiting inspection.",
            "approved": "Claim approved. Repair work can begin.",
            "rejected": "Claim rejected. Please contact customer support for details.",
            "completed": "Claim completed. Vehicle repaired and delivered."
        }
        
        return {
            "claim_id": claim_id,
            "vehicle_registration": claim_info['vehicle_registration'],
            "vehicle_model": vehicle_model,
            "claim_type": claim_info['claim_type'].replace('_', ' ').title(),
            "description": claim_info['description'],
            "filing_date": claim_info['filing_date'],
            "status": claim_info['status'].title(),
            "status_message": status_messages.get(claim_info['status'], "Status unknown"),
            "service_center": claim_info['service_center'],
            "estimated_cost": f"₹{claim_info['estimated_cost']:,}" if claim_info['estimated_cost'] > 0 else "To be estimated",
            "resolution_date": claim_info['resolution_date'] if claim_info['resolution_date'] else "Pending"
        }
        
    except Exception as e:
        return {"error": f"An error occurred while retrieving claim status: {str(e)}"}


def handle_tool_error(state) -> dict:
    error = state.get("error")
    tool_calls = state["messages"][-1].tool_calls
    return {
        "messages": [
            ToolMessage(
                content=f"Error: {repr(error)}\n please fix your mistakes.",
                tool_call_id=tc["id"],
            )
            for tc in tool_calls
        ]
    }


def create_tool_node_with_fallback(tools: list) -> dict:
    """
    Create a ToolNode with error handling fallback for a list of tools.

    This function creates a ToolNode from the given list of tools and adds
    an error handling fallback. If a tool execution fails, it will catch
    the error and return a message asking to fix the mistake.

    Args:
        tools (list): A list of tool objects to be used in the ToolNode.

    Returns:
        dict: A ToolNode object with error handling fallback.

    The returned ToolNode will:
    1. Attempt to execute the appropriate tool based on the input.
    2. If an error occurs, it will use the handle_tool_error function to
       generate an error message.
    3. The error message will be returned as a ToolMessage.

    Note: This function relies on the ToolNode class from langgraph.prebuilt
    and the RunnableLambda class from langchain_core.runnables.
    """

    return ToolNode(tools).with_fallbacks([RunnableLambda(handle_tool_error)], exception_key="error")


def _print_event(event: dict, _printed: set, max_length=1500):
    current_state = event.get("dialog_state")
    if current_state:
        print("Currently in: ", current_state[-1])
    message = event.get("messages")
    if message:
        if isinstance(message, list):
            message = message[-1]
        if message.id not in _printed:
            msg_repr = message.pretty_repr(html=True)
            if len(msg_repr) > max_length:
                msg_repr = msg_repr[:max_length] + " ... (truncated)"
            print(msg_repr)
            _printed.add(message.id)


class State(TypedDict):
    messages: Annotated[list[AnyMessage], add_messages]



def update_tool_messages(message):



    # for message in tool_messages:
    content = str(message.content)

    # Initialize a list to store the extracted IDs
    extracted_info = []
    combined_info = []
    # Regular expressions to extract the information
    booking_ids = re.findall(r'"booking_id":\s*(\d+)', content)
    car_ids = re.findall(r'"car_id":\s*(\d+)', content)
    names = re.findall(r'"name":\s*"(.*?)"', content)
    start_dates = re.findall(r'"start_date":\s*"(.*?)"', content)
    end_dates = re.findall(r'"end_date":\s*"(.*?)"', content)

    # Maximum length of extracted lists to handle cases where some fields are missing
    max_len = max(len(booking_ids), len(car_ids), len(names), len(start_dates), len(end_dates))

    # Combine extracted information into dictionaries, handling missing fields
    for i in range(max_len):
        booking_dict = {}
        if i < len(booking_ids):
            booking_dict['booking_id'] = int(booking_ids[i])
        if i < len(car_ids):
            booking_dict['car_id'] = int(car_ids[i])
        if i < len(names):
            booking_dict['name'] = names[i]
        if i < len(start_dates):
            booking_dict['start_date'] = start_dates[i]
        if i < len(end_dates):
            booking_dict['end_date'] = end_dates[i]

        combined_info.append(booking_dict)

    # Convert the extracted information to a JSON string
    if combined_info:
        content = json.dumps(combined_info)

    # Update the message with the filtered content
    message.content = content
    # updated_messages.append(updated_message)

    return message


def clean_state(state):
    cleaned_messages = []
    middle_steps = []
    users = 0
    bots = 0

    for message in state.get("messages"):
        # Identify user input
        if isinstance(message, HumanMessage):
            user_input = message
            cleaned_messages.append(user_input)
            users += 1

        # Identify bot response
        elif isinstance(message, AIMessage):
            if message.content and message.response_metadata:
                # Before appending the bot's response, ensure any middle_steps are added
                cleaned_messages.append(message)
                bots += 1

                # After appending, if users == bots, update and append middle_steps
                if users == bots:
                    # Update ToolMessages in middle_steps if necessary

                    for index, step in enumerate(cleaned_messages):
                        if isinstance(step, ToolMessage):
                            if ('booking_id' in str(step.content)) or ('car_id' in str(step.content)):
                                print("************************** found it******")
                                print("step : ", step)
                                print("update_tool_messages(step) : ", update_tool_messages(step))
                                cleaned_messages[index] = update_tool_messages(step)
                        # Replace the middle_steps with their updated versions
                    cleaned_messages = [msg for msg in cleaned_messages if msg not in middle_steps]
                    middle_steps = []
            else:
                cleaned_messages.append(message)
                middle_steps.append(message)

        # Identify tool-related messages (middle steps)
        elif isinstance(message, ToolMessage):
            if ('booking_id' in str(message.content)) or ('car_id' in str(message.content)):
                # middle_steps.append(message)
                cleaned_messages.append(message)
            else:
                middle_steps.append(message)
                cleaned_messages.append(message)
            # Appending immediately, but will be updated later

    return {'messages': cleaned_messages}

def clean_state2(state):
    cleaned_messages = []
    middle_steps = []
    users = 0
    bots = 0

    for message in state.get("messages"):
        # Identify user input
        if isinstance(message, HumanMessage):
            user_input = message
            cleaned_messages.append(user_input)
            users += 1

        # Identify bot response
        elif isinstance(message, AIMessage):
            if message.content and message.response_metadata:
                # Before appending the bot's response, ensure any middle_steps are added
                cleaned_messages.append(message)
                bots += 1

                # After appending, if users == bots, update and append middle_steps
                if users == bots:
                    cleaned_messages = [msg for msg in cleaned_messages if msg not in middle_steps]
                    middle_steps = []
            else:
                cleaned_messages.append(message)
                middle_steps.append(message)

        # Identify tool-related messages (middle steps)
        elif isinstance(message, ToolMessage):
                middle_steps.append(message)
                cleaned_messages.append(message)
            # Appending immediately, but will be updated later

    return {'messages': cleaned_messages}
class Assistant:
    def __init__(self, runnable: Runnable):
        self.runnable = runnable

    def __call__(self, state: State, config: RunnableConfig):
        while True:
            configuration = config.get("configurable", {})
            passenger_id = configuration.get("user_info", None)
            state = {**state, "user_info": passenger_id}
            state = clean_state(state)
            for e in state.get("messages"):
                print(e,'\n\n')

            if len(state.get("messages")) >= 2:
                if state.get("messages")[-2].response_metadata:
                    tokens = state.get("messages")[-2].response_metadata['token_usage']['total_tokens']
                    if tokens < 7000 and tokens > 5000:
                        state["messages"] = state.get("messages")[-3:]
                    elif tokens > 7000:
                        state = clean_state2(state)
                        state["messages"] = state.get("messages")[-4:]


            try :
                result = self.runnable.invoke(state)
            except Exception as e:
                print("--------------------------\n",e)
                print(f"Error in Assistant: {str(e)}")
                result = AIMessage(content="I apologize for the inconvenience. I'm having trouble processing your request right now. Could you please try rephrasing your question or providing more details?")
                print("\nclearing\n---------------------")
                break
            # If the LLM happens to return an empty response, we will re-prompt it
            # for an actual response and remove the empty result from the history.
            if not result.tool_calls and (
                    not result.content
                    or isinstance(result.content, list)
                    and not result.content[0].get("text")
            ):
                # Re-prompt for a real output
                state["messages"].append(("user", "Respond with a real output."))
            else:
                # After receiving a real output, remove the "Respond with a real output." from history
                state["messages"] = [
                    message for message in state["messages"]
                    if message != ("user", "Respond with a real output.")
                ]
                break

        return {"messages": result}




primary_assistant_prompt = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            "You are a knowledgeable and empathetic customer support specialist for **Car Warranty Services**, "
            "expert in Extended Warranty and Customer Convenience Package (CCP) services. "
            "Your primary goal is to help customers understand, purchase, and utilize their warranty benefits effectively."
            
            "\n\n### Core Knowledge Base:\n"
            "1. **Standard Warranty**: All new vehicles come with 3 years or 100,000 km warranty (whichever comes first)\n"
            "2. **Extended Warranty**: Extends coverage from 3 to 6 years, up to 160,000 km. Can be purchased anytime within first 3 years\n"
            "3. **CCP Requirements**: \n"
            "   - **MUST have Extended Warranty first** (non-negotiable prerequisite)\n"
            "   - Purchase within 1 year 9 months (21 months) of vehicle purchase date\n"
            "   - Three packages: 1 Year (₹3,500), 2 Year (₹5,500), 3 Year (₹7,500)\n"
            "4. **CCP Coverage**: Engine damage from water entry (hydrolock), adulterated fuel, rodent damage, insect damage\n"
            "5. **Claim Process**: Report immediately → Visit service center → Inspection (24-48 hrs) → Approval (5-7 days)\n"
            
            "\n\n### Your Capabilities:\n"
            "**Warranty & CCP Management:**\n"
            "- **Check CCP Eligibility**: Verify if vehicle qualifies for CCP purchase\n"
            "- **Check Extended Warranty Eligibility**: Verify if vehicle qualifies for Extended Warranty\n"
            "- **Purchase CCP Package**: Process CCP package purchase (after eligibility verification)\n"
            "- **Check Warranty Status**: View current warranty and CCP status for any vehicle\n"
            "- **File CCP Claim**: Submit claims for water/fuel/rodent/insect damage\n"
            "- **Get Coverage Details**: Explain what Extended Warranty and CCP cover\n"
            "- **Show My Warranties**: Display all warranties for user's vehicles\n"
            "- **Show My Claims**: Display all CCP claims with current status\n"
            "- **Show My Vehicles**: Display all vehicles registered under user account\n"
            "- **Get Claim Status**: Check detailed status of specific claim\n"
            "- **Cancel Warranty Service**: Cancel pending warranty purchases\n"
            "- **Lookup Policy**: Check company policies for warranty services\n"
            "\n"
            "**Service Center Appointments:**\n"
            "- **Find Service Center**: Locate nearest authorized service centers\n"
            "- **Check Service Center Availability**: View available appointment slots at service centers\n"
            "- **Book Service Appointment**: Schedule appointments for warranty inspections, claim assessments, or general service\n"
            "- **View My Appointments**: Display all customer appointments with status\n"
            "- **Cancel Appointment**: Cancel scheduled appointments\n"
            "- **Reschedule Appointment**: Change appointment date and time\n"
            "\n"
            "**Email Notifications:**\n"
            "- **Send Email Notification**: Send warranty updates, claim status, purchase confirmations, and appointment reminders via email\n"
            "- Use for: Warranty expiry reminders, claim updates, purchase confirmations, appointment confirmations\n"
            "- Automatically formats professional HTML emails with templates\n"
            
            "\n\n### Interaction Guidelines:\n"
            "- Always verify eligibility before making recommendations\n"
            "- Explain coverage in simple, customer-friendly terms with examples\n"
            "- Use clear markdown formatting for better readability\n"
            "- Always mention deadlines and purchase windows prominently\n"
            "- Be empathetic when handling claim-related queries\n"
            "- Format all monetary values in Indian Rupees (₹)\n"
            "- Use dd/mm/YYYY format for all dates\n"
            "- Greet users warmly - you can respond to greetings naturally without using tools\n"
            "\n"
            "**IMPORTANT - Email Confirmations:**\n"
            "- When filing claims or booking appointments, the system AUTOMATICALLY sends email confirmations\n"
            "- You do NOT need to ask the user for their email - it's auto-detected from their profile\n"
            "- After filing a claim or booking appointment, inform the user: 'A confirmation email has been sent to your registered email address'\n"
            "- The tools return 'email_confirmation' status - mention this naturally in your response\n"
            "- Be conversational: 'Great! Your claim is filed. You'll receive a confirmation email with all the details shortly.'\n"
            
            "\n\n### Critical Business Rules:\n"
            "- **NO CCP WITHOUT EXTENDED WARRANTY** - This is absolutely non-negotiable\n"
            "- Extended Warranty must be purchased within 3 years of vehicle purchase\n"
            "- CCP must be purchased within 21 months of vehicle purchase\n"
            "- All services valid only at authorized service centers\n"
            "- Claims require active CCP coverage at time of incident\n"
            
            "\n\n### Response Formatting:\n"
            "Use markdown to structure responses:\n"
            "- Use **bold** for important information\n"
            "- Use bullet points for lists\n"
            "- Use ### for section headings\n"
            "- DO NOT Use emojis in any response\n"
            
            "\n\nCurrent customer:\n\n{user_info}\n"
            "\nCurrent date (dd/mm/YYYY): {time}.",
        ),
        ("placeholder", "{messages}"),
    ]
).partial(user_info=user_info, time=datetime.now().strftime('%d/%m/%Y'))

part_1_tools = [
    # Warranty & CCP management tools
    check_ccp_eligibility,
    purchase_ccp_package,
    check_warranty_status,
    cancel_warranty_service,
    file_ccp_claim,
    check_extended_warranty_eligibility,
    get_coverage_details,
    find_service_center,
    show_my_warranties,
    show_my_claims,
    show_my_vehicles,
    get_claim_status,
    show_customer_info,
    lookup_policy,
    calculator,
    dates_calculator,
    # Service center appointment tools (FREE - CSV-based)
    check_service_center_availability,
    book_service_appointment,
    view_my_appointments,
    cancel_appointment,
    reschedule_appointment,
    # Email notification tool (FREE with Gmail SMTP)
    send_email_notification,
]
part_1_assistant_runnable = primary_assistant_prompt | llm.bind_tools(part_1_tools)

builder = StateGraph(State)

# Define nodes: these do the work
builder.add_node("assistant", Assistant(part_1_assistant_runnable))
builder.add_node("tools", create_tool_node_with_fallback(part_1_tools))
# Define edges: these determine how the control flow moves
builder.add_edge(START, "assistant")
builder.add_conditional_edges(
    "assistant",
    tools_condition,
)
builder.add_edge("tools", "assistant")

# The checkpointer lets the graph persist its state
# this is a complete memory for the entire graph.
memory = MemorySaver()

part_1_graph = builder.compile(checkpointer=memory)



