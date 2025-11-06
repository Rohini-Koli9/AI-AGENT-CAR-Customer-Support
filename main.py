import streamlit as st
import pandas as pd
import os
from streamlit_option_menu import option_menu

# Must be the first Streamlit command
st.set_page_config(page_title='Car Warranty Support', page_icon='🚗', layout='centered')

# Initialize session state
if 'logged_in' not in st.session_state:
    st.session_state['logged_in'] = False
if 'user' not in st.session_state:
    st.session_state['user'] = None
if 'page' not in st.session_state:
    st.session_state['page'] = 'Login'

# Define paths
users_csv_path = 'Car-Warranty-System/data/users.csv'
USER_ID_FILE_PATH = 'Car-Warranty-System/data/user_id.conf'

# Load user data
if os.path.exists(users_csv_path):
    users_df = pd.read_csv(users_csv_path)
else:
    users_df = pd.DataFrame(columns=['user_id', 'name', 'email', 'phone', 'address'])

# Data files are already created in the data folder


# ============ LOGIN PAGE ============
if not st.session_state['logged_in']:
    # Hide the sidebar
    st.markdown(
        """
        <style>
        [data-testid="stSidebar"] {
            display: none;
        }
        </style>
        """,
        unsafe_allow_html=True
    )
    
    if st.session_state['page'] == 'Login':
        st.title("Car Warranty & CCP Support")
        st.subheader("Login or Register")

        # Login Section
        email = st.text_input("Email", key="login_email")

        # Buttons layout
        col1, col2 = st.columns([3, 1])

        with col1:
            login_button = st.button("Login", type="primary")
        with col2:
            register_button = st.button("Register")

        if login_button:
            if email:
                user = users_df[users_df['email'] == email]
                if not user.empty:
                    st.session_state['user'] = user.iloc[0].to_dict()
                    st.session_state['logged_in'] = True
                    
                    # Save user ID
                    os.makedirs(os.path.dirname(USER_ID_FILE_PATH), exist_ok=True)
                    with open(USER_ID_FILE_PATH, 'w') as file:
                        file.write(str(st.session_state['user']['user_id']))
                    
                    os.environ['USER_ID_FILE'] = USER_ID_FILE_PATH
                    st.success(f"Welcome back, {st.session_state['user']['name']}!")
                    st.rerun()
                else:
                    st.error("Email not found. Please register.")
            else:
                st.error("Please enter an email.")

        if register_button:
            st.session_state['page'] = 'Register'
            st.rerun()

    elif st.session_state['page'] == 'Register':
        st.title("Register")

        # Registration Form
        full_name = st.text_input("Full Name")
        email = st.text_input("Email")
        phone = st.text_input("Phone")
        address = st.text_input("Address")

        col1, col2 = st.columns([1, 1])
        with col1:
            if st.button("Submit Registration", type="primary"):
                if full_name and email and phone and address:
                    # Check if email already exists
                    if email in users_df['email'].values:
                        st.error("Email already registered. Please login.")
                    else:
                        # Determine new user ID
                        if not users_df.empty:
                            new_user_id = users_df['user_id'].max() + 1
                        else:
                            new_user_id = 101

                        # Append new user
                        new_user = pd.DataFrame({
                            'user_id': [new_user_id],
                            'name': [full_name],
                            'email': [email],
                            'phone': [phone],
                            'address': [address]
                        })

                        users_df = pd.concat([users_df, new_user], ignore_index=True)
                        users_df.to_csv(users_csv_path, index=False)

                        st.success("Registration successful! You can now log in.")
                        st.session_state['page'] = 'Login'
                        st.rerun()
                else:
                    st.error("Please fill out all fields.")
        
        with col2:
            if st.button("Back to Login"):
                st.session_state['page'] = 'Login'
                st.rerun()


# ============ MAIN APP ============
else:
    # User is logged in
    user_name = st.session_state['user']['name']
    
    # Sidebar
    st.sidebar.header(f"Hello, {user_name}")
    
    # Define pages - Only Customer Support is functional with warranty system
    pages = {
        "Customer Support": "Car-Warranty-System/pages/customer_support.py",
    }
    
    # Navigation menu
    with st.sidebar:
        selected_option = option_menu(
            menu_title=None,
            options=list(pages.keys()),
            icons=["chat"],
            default_index=0,
            orientation="vertical",
            key="main_menu"
        )
    
    # Logout button
    if st.sidebar.button("Logout", type="secondary"):
        # Clear session
        st.session_state['logged_in'] = False
        st.session_state['user'] = None
        st.session_state['page'] = 'Login'
        
        # Clear user ID file
        if os.path.exists(USER_ID_FILE_PATH):
            try:
                os.remove(USER_ID_FILE_PATH)
            except:
                pass
        
        st.rerun()
    
    # Load selected page
    if selected_option:
        page_path = pages[selected_option]
        if os.path.exists(page_path):
            with open(page_path) as f:
                code = f.read()
                # Remove any set_page_config calls from the loaded page
                code_lines = code.split('\n')
                filtered_code = '\n'.join([line for line in code_lines 
                                          if 'set_page_config' not in line])
                exec(filtered_code)
        else:
            st.error(f"Page not found: {page_path}")
