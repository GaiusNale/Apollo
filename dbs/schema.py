"""
This file initializes the setup for the MongoDB connection and defines the document structure used in the cogs directory.
It establishes a connection to the MongoDB database using credentials from environment variables and defines the Ticket document schema.
"""

from mongoengine import (
    connect,  # Used to connect to the MongoDB database
    Document,  # Base class for creating MongoDB documents
    StringField,  # Defines a string field in a document
    IntField,  # Defines an integer field in a document
    DateTimeField,  # Defines a datetime field in a document
    BooleanField,  # Defines a boolean field in a document
    ReferenceField,  # Used to create references between documents (not used in this schema)
    ListField,  # Defines a list field in a document
)
from decouple import config  # Used to securely retrieve environment variables
from datetime import datetime  # Used to handle date and time for documents

# ----- Database Connection Setup -----

# These values are retrieved from environment variables for security and flexibility.
DB_NAME = config("DB_NAME", default=None)  # Name of the MongoDB database
DB_USERNAME = config("DB_USERNAME", default=None)  # Username for database authentication
DB_PASSWORD = config("DB_PASSWORD", default=None)  # Password for database authentication
DB_HOST = config("DB_HOST", default=None)  # Host where MongoDB is running
DB_PORT = int(config("DB_PORT", default=27017))  # Port where MongoDB is running (default is 27017)

# Connect to the MongoDB database using the provided credentials and host information.
connect(
    db=DB_NAME,
    username=DB_USERNAME,
    password=DB_PASSWORD,
    host=DB_HOST,
    port=DB_PORT,
)

# ----- Document Definitions -----

# Ticket class represents a ticket in the system. Each ticket is a document in the 'tickets' collection.
class Ticket(Document):
    title = StringField(required=True)  # Title of the ticket, required field
    description = StringField(required=True)  # Description of the issue or request, required field
    creator_id = StringField(required=True)  # ID of the user who created the ticket, required field
    status = StringField(default="open")  # Status of the ticket, default is "open"
    created_at = DateTimeField(default=datetime.utcnow)  # Timestamp when the ticket was created, defaults to current UTC time
    closed_at = DateTimeField(null=True)  # Timestamp when the ticket was closed, initially null

    # Meta information about the document, including the MongoDB collection name.
    meta = {'collection': 'tickets'}

    # Method to close the ticket. Updates the status and sets the closed_at timestamp.
    def close_ticket(self):
        self.status = "closed"  # Set status to "closed"
        self.closed_at = datetime.utcnow()  # Record the current time as the close time
        self.save()  # Save the changes to the database

    # String representation of the Ticket object for easy debugging and logging.
    def __str__(self):
        return f"Ticket(title={self.title}, creator_id={self.creator_id}, status={self.status})"

    # Static method to create a new ticket. Returns the created ticket.
    @staticmethod
    def create_ticket(title, description, creator_id):
        ticket = Ticket(title=title, description=description, creator_id=creator_id)  # Create a new Ticket instance
        ticket.save()  # Save the ticket to the database
        return ticket  # Return the saved ticket

    # Static method to retrieve all open tickets from the database.
    @staticmethod
    def get_open_tickets():
        return Ticket.objects(status="open")  # Query the database for all tickets with status "open"

    # Static method to retrieve a ticket by its ID.
    @staticmethod
    def get_ticket_by_id(ticket_id):
        return Ticket.objects(id=ticket_id).first()  # Query the database for a ticket with the given ID and return the first match
