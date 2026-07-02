#streamlit14.py


import streamlit as st
import pandas as pd
from agents import ClassifierAgent, FeedbackAgent, QueryAgent, TicketDatabase, log_feedback_interaction
from datetime import datetime

# Initialize agents and ticket DB
classifier = ClassifierAgent()
feedback_agent = FeedbackAgent()
query_agent = QueryAgent()
ticket_db = TicketDatabase()

# Admin password (for demo only; use env vars in production)
ADMIN_PASSWORD = "SesameStreet"

# Initialize session state
if 'chat_history' not in st.session_state:
    st.session_state.chat_history = []
if 'current_intent' not in st.session_state:
    st.session_state.current_intent = None
if 'admin_logged_in' not in st.session_state:
    st.session_state.admin_logged_in = False

# Ticket flow session variables
if 'ticket_number_entered' not in st.session_state:
    st.session_state.ticket_number_entered = False
if 'ticket_number' not in st.session_state:
    st.session_state.ticket_number = ""
if 'awaiting_update_choice' not in st.session_state:
    st.session_state.awaiting_update_choice = False
if 'awaiting_status_update' not in st.session_state:
    st.session_state.awaiting_status_update = False

def display_chat():
    for entry in st.session_state.chat_history:
        st.markdown(f"**Intent:** {entry['intent']}")
        st.markdown(f"**User Input:** {entry['input']}")
        st.markdown(f"**Agent Response:** {entry['response']}")
        st.markdown("---")

def get_current_tickets():
    try:
        df = pd.read_csv(ticket_db.db_file)
        return df
    except Exception:
        return pd.DataFrame(columns=['TicketNumber', 'Status'])

def reset_ticket_flow():
    st.session_state.ticket_number_entered = False
    st.session_state.ticket_number = ""
    st.session_state.awaiting_update_choice = False
    st.session_state.awaiting_status_update = False
    st.session_state.current_intent = None

def show_customer_interface():
    st.subheader("CUSTOMER: Welcome! Please Select Your Request!")
    col1, col2, col3 = st.columns(3)
    with col1:
        if st.button("Ticket", key="btn_ticket"):
            reset_ticket_flow()
            st.session_state.current_intent = "Ticket"
    with col2:
        if st.button("Feedback", key="btn_feedback"):
            st.session_state.current_intent = "Feedback"
    with col3:
        if st.button("Exit/Reset", key="btn_exit_reset"):
            reset_ticket_flow()
            st.session_state.current_intent = None

    if st.session_state.current_intent == "Ticket":
        st.subheader("Ticket Options")
        option = st.radio("Choose an option:", ["Existing Ticket", "New Ticket"], key="ticket_option")

        if option == "Existing Ticket":
            if not st.session_state.ticket_number_entered:
                ticket_number = st.text_input("Please enter your 6-digit ticket number:", key="input_ticket_number")
                if st.button("Submit Ticket Number", key="btn_submit_ticket_number"):
                    if ticket_number.strip() and len(ticket_number.strip()) == 6 and ticket_number.strip().isdigit():
                        st.session_state.ticket_number = ticket_number.strip()
                        st.session_state.ticket_number_entered = True
                        st.session_state.awaiting_update_choice = True
                        st.rerun()
                    else:
                        st.warning("Please enter a valid 6-digit ticket number.")
            elif st.session_state.awaiting_update_choice:
                status = query_agent.get_ticket_status_by_number(st.session_state.ticket_number)
                if status:
                    st.write(f"Your ticket #{st.session_state.ticket_number} is currently **{status}**.")
                else:
                    st.write(f"Ticket #{st.session_state.ticket_number} is not found.")

                col1, col2 = st.columns(2)
                with col1:
                    if st.button("Change Update", key="btn_change_update"):
                        st.session_state.awaiting_update_choice = False
                        st.session_state.awaiting_status_update = True
                        st.rerun()
                with col2:
                    if st.button("Back to Ticket Options", key="btn_back_ticket_options_1"):
                        reset_ticket_flow()
                        st.session_state.current_intent = "Ticket"
                        st.rerun()
            elif st.session_state.awaiting_status_update:
                status_options = ['Resolved', 'Unresolved']
                new_status = st.selectbox("Select new status:", status_options, key="select_status")
                if st.button("Submit Update", key="btn_submit_update"):
                    updated = ticket_db.update_ticket_status(st.session_state.ticket_number, new_status=new_status)
                    if updated:
                        response = f"Ticket #{st.session_state.ticket_number} status updated to {new_status}!"
                    else:
                        response = f"Ticket #{st.session_state.ticket_number} not found."
                    st.session_state.chat_history.append({
                        'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                        'intent': 'Ticket Update',
                        'input': f"Ticket #{st.session_state.ticket_number} -> {new_status}",
                        'response': response
                    })
                    st.write(response)
                    col1, col2 = st.columns(2)
                    with col1:
                        if st.button("Update Another Status", key="btn_update_another"):
                            st.session_state.awaiting_status_update = False
                            st.session_state.awaiting_update_choice = True
                            st.rerun()
                    with col2:
                        if st.button("Back to Ticket Options", key="btn_back_ticket_options_2"):
                            reset_ticket_flow()
                            st.session_state.current_intent = "Ticket"
                            st.rerun()

        elif option == "New Ticket":
            st.subheader("Submit a New Ticket")
            issue_description = st.text_area("Please describe your issue:", key="textarea_new_ticket")
            if st.button("Submit Ticket", key="btn_submit_new_ticket"):
                if issue_description.strip():
                    response = feedback_agent.handle_negative_feedback()
                    classification = 'Negative Feedback'  # For logging consistency
                    st.session_state.chat_history.append({
                        'intent': 'New Ticket',
                        'input': issue_description,
                        'response': response,
                        'classification': classification
                    })
                    # Log feedback interaction with ticket created = Yes
                    log_feedback_interaction(issue_description, response, 'Yes')
                    st.write(response)
                    if st.button("Back to Ticket Options", key="btn_back_ticket_options_3"):
                        reset_ticket_flow()
                        st.session_state.current_intent = "Ticket"
                        st.rerun()
                else:
                    st.warning("Please describe your issue.")

    elif st.session_state.current_intent == "Feedback":
        st.subheader("Customer Feedback")
        feedback_input = st.text_area("How did we do?", key="textarea_feedback")
        if st.button("Submit Feedback", key="btn_submit_feedback"):
            if feedback_input.strip():
                classification = classifier.classify_message(feedback_input)
                if classification == 'Positive Feedback':
                    customer_name = classifier.extract_customer_name(feedback_input)
                    response = feedback_agent.handle_positive_feedback(customer_name=customer_name)
                    ticket_action = 'No'
                else:
                    response = feedback_agent.handle_negative_feedback()
                    ticket_action = 'Yes'
                st.session_state.chat_history.append({
                    'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                    'intent': 'Feedback',
                    'input': feedback_input,
                    'response': response,
                    'classification': classification
                })
                # Log feedback interaction
                log_feedback_interaction(feedback_input, response, ticket_action)
                st.rerun()
            else:
                st.warning("Please let us know how we did! We welcome suggestions for improvements!")

    st.subheader("Conversation History")
    display_chat()

def logout():
    st.session_state.admin_logged_in = False
    st.session_state.current_intent = None
    st.session_state.chat_history = []

if not st.session_state.admin_logged_in:
    st.title("Customer Ticket Support \n   by OPENAI and Simplilearn for the Bankers UniversALL Virtua")
    pwd = st.text_input("Evaluation and Logs (Team Members ONLY)", type="password", key="input_admin_password")
    if st.button("ADMIN Login", key="btn_login_admin"):
        if pwd == ADMIN_PASSWORD:
            st.session_state.admin_logged_in = True
            st.success("Password Accepted! WB, Team!")
            st.rerun()
        else:
            st.error("Incorrect. Please enter the correct password or contact your supervisor.")
    else:
        show_customer_interface()
else:
    st.sidebar.button("Logout", on_click=logout, key="btn_logout")

    st.title("Employees Only: Evaluation & Logs")

    st.subheader("Evaluation and Logs")
    if st.session_state.chat_history:
        logs_df = pd.DataFrame(st.session_state.chat_history)
        st.dataframe(logs_df)
    else:
        st.write("No interactions logged yet.")

    st.subheader("All Support Tickets")
    tickets_df = get_current_tickets()
    if tickets_df.empty:
        st.write("No tickets found.")
    else:
        st.dataframe(tickets_df)

    st.markdown("---")
    st.markdown("### Customer Interface (for testing)")
    show_customer_interface()
