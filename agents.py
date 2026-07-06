import csv # For storing ticketnumbers and their statuses
import os # For functions to ineract with the operating system
import random #To generate new ticket numbers without conflicting with existing ones
import re # Regulate expression module for the 6-digit tickt numbers
import openai # GPT 4.0 LLM stuff
from textblob import TextBlob # For better sentiment detection
from datetime import datetime # For timestamping feedback 

TICKET_DB_FILE = 'support_tickets.csv'
FEEDBACK_LOG_FILE = 'feedback_log.csv'

openai.api_key = os.getenv("OPENAI_API_KEY")

class TicketDatabase:
    def __init__(self, db_file=TICKET_DB_FILE):
        self.db_file = db_file
        try:
            if not os.path.exists(self.db_file):
                with open(self.db_file, mode='w', newline='') as file:
                    writer = csv.writer(file)
                    writer.writerow(['TicketNumber', 'Status'])  # Columns
        except Exception as e:
            print(f"Error initializing ticket database: {e}")

    def insert_ticket(self, ticket_number, status='Unresolved'):
        try:
            with open(self.db_file, mode='a', newline='') as file:
                writer = csv.writer(file)
                writer.writerow([ticket_number, status])
        except Exception as e:
            print(f"Error inserting ticket: {e}")

    def get_ticket_status(self, ticket_number):
        try:
            with open(self.db_file, mode='r') as file:
                reader = csv.DictReader(file)
                for row in reader:
                    if row['TicketNumber'] == ticket_number:
                        return row['Status']
            return None
        except Exception as e:
            print(f"Error reading ticket status: {e}")
            return None

    def update_ticket_status(self, ticket_number, new_status='Resolved'):
        try:
            tickets = []
            updated = False
            with open(self.db_file, mode='r') as file:
                reader = csv.DictReader(file)
                for row in reader:
                    if row['TicketNumber'] == ticket_number:
                        row['Status'] = new_status
                        updated = True
                    tickets.append(row)
            if updated:
                with open(self.db_file, mode='w', newline='') as file:
                    writer = csv.DictWriter(file, fieldnames=['TicketNumber', 'Status'])
                    writer.writeheader()
                    writer.writerows(tickets)
            return updated
        except Exception as e:
            print(f"Error updating ticket status: {e}")
            return False

def log_feedback_interaction(user_feedback, agent_response, ticket_action):
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    try:
        file_exists = os.path.exists(FEEDBACK_LOG_FILE)
        with open(FEEDBACK_LOG_FILE, mode='a', newline='') as file:
            writer = csv.writer(file)
            if not file_exists:
                writer.writerow(['Timestamp', 'UserFeedback', 'AgentResponse', 'TicketAction'])
            writer.writerow([timestamp, user_feedback, agent_response, ticket_action])
    except Exception as e:
        print(f"Error logging feedback interaction: {e}")

class ClassifierAgent:
    def fallback_sentiment(self, message):
        analysis = TextBlob(message)
        polarity = analysis.sentiment.polarity
        if polarity > 0.1:
            return 'Positive Feedback'
        elif polarity < -0.1:
            return 'Negative Feedback'
        else:
            return 'Query'

    def classify_message(self, message):
        prompt = (
            "You are a helpful assistant for a bank's customer support.\n"
            "Classify the following customer message into one of three categories:\n"
            " - Positive Feedback: Customer expresses satisfaction, thanks, or praise.\n"
            " - Negative Feedback: Customer expresses complaints, issues, or dissatisfaction.\n"
            " - Query: Customer asks questions, requests ticket status, or needs help.\n\n"
            "Examples:\n"
            "Message: 'Thanks for resolving my issue!' -> Positive Feedback\n"
            "Message: 'I am very unhappy with the delay.' -> Negative Feedback\n"
            "Message: 'What is the status of my ticket 123456?' -> Query\n"
            "Message: 'I want to report a problem with my card.' -> Negative Feedback\n"
            "Message: 'Great service, thanks!' -> Positive Feedback\n"
            "Message: 'Can you check ticket 654321?' -> Query\n\n"
            f"Message: \"{message}\"\n"
            "Category (only one):"
        )
        try:
            response = openai.ChatCompletion.create(
                model="gpt-4",
                messages=[
                    {"role": "system", "content": "You assist banking customer support by classifying messages into feedback or queries."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=20,
                temperature=0,
            )
            classification = response.choices[0].message['content'].strip().lower()
            if 'positive' in classification:
                return 'Positive Feedback'
            elif 'negative' in classification:
                return 'Negative Feedback'
            elif 'query' in classification:
                return 'Query'
            else:
                return self.fallback_sentiment(message)
        except Exception:
            return self.fallback_sentiment(message)

    def extract_customer_name(self, message):
        patterns = [
            r"\bI am (\w+)\b",
            r"\bMy name is (\w+)\b",
            r"\bThis is (\w+)\b",
            r"\bIt's (\w+)\b"
        ]
        for pattern in patterns:
            match = re.search(pattern, message, re.IGNORECASE)
            if match:
                return match.group(1)
        return "Customer"

class FeedbackAgent:
    def __init__(self):
        self.ticket_db = TicketDatabase()

    def generate_ticket_number(self):
        while True:
            ticket_number = str(random.randint(100000, 999999))
            if self.ticket_db.get_ticket_status(ticket_number) is None:
                return ticket_number

    def handle_positive_feedback(self, customer_name='Customer'):
        return f"Thank you, {customer_name}!"

    def handle_negative_feedback(self):
        ticket_number = self.generate_ticket_number()
        self.ticket_db.insert_ticket(ticket_number, status='Unresolved')
        return f"We apologize for the inconvenience! A new ticket #{ticket_number} has been generated to address your concerns. Someone from our team will contact you."

class QueryAgent:
    def __init__(self):
        self.ticket_db = TicketDatabase()

    def extract_ticket_number(self, message):
        match = re.search(r'\b\d{6}\b', message)
        if match:
            return match.group(0)
        return None

    def handle_query(self, message):
        ticket_number = self.extract_ticket_number(message)
        if ticket_number:
            status = self.ticket_db.get_ticket_status(ticket_number)
            if status:
                return f"Your ticket #{ticket_number} is currently {status}."
            else:
                return f"Ticket #{ticket_number} not found. Please enter again or visit the front desk for live help."
        else:
            return ("I couldn't find a ticket number in your message. "
                    "If you want to report a new issue, please select the Feedback option for a new ticket number. "
                    "You can also describe your problem there.")

    def handle_update(self, message):
        update_keywords = ['close', 'resolve', 'resolved', "don't need help", 'mark as resolved', 'finish']
        if any(keyword in message.lower() for keyword in update_keywords):
            ticket_number = self.extract_ticket_number(message)
            if ticket_number:
                updated = self.ticket_db.update_ticket_status(ticket_number, new_status='Resolved')
                if updated:
                    return f"Ticket #{ticket_number} is now Resolved. Thank you for the update!"
                else:
                    return f"Ticket #{ticket_number} not found."
            else:
                return "Please provide a valid 6-digit ticket number."
        return None  # No update intent detected

    def handle_follow_up_ticket_number(self, ticket_number):
        status = self.ticket_db.get_ticket_status(ticket_number)
        if status:
            return f"Your ticket #{ticket_number} is currently {status}. Would you like to update its status?"
        else:
            return f"Ticket #{ticket_number} not recognized. Please try again?"

    def get_ticket_status_by_number(self, ticket_number):
        return self.ticket_db.get_ticket_status(ticket_number)

