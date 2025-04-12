import os
import re
import json
import time
from dotenv import load_dotenv
from datetime import datetime
from tqdm.auto import tqdm  # For progress bars

from pinecone import Pinecone, ServerlessSpec
from openai import OpenAI

# --- Configuration ---
PINECONE_INDEX_NAME = "meeting-asst-spc"
OPENAI_EMBEDDING_MODEL = "text-embedding-3-small"
# text-embedding-3-small has a dimension of 1536
# text-embedding-3-large has a dimension of 3072
# text-embedding-ada-002 has a dimension of 1536
EMBEDDING_DIMENSION = 1536
PINECONE_CLOUD = "aws" # Specify your cloud provider
PINECONE_REGION = "us-east-1" # Specify your region

MEETING_TRANSCRIPTS_PATH = "data/meeting_transcripts.txt"
JIRA_TICKETS_PATH = "data/jira_tickets.json"
UPSERT_BATCH_SIZE = 100 # Upsert vectors in batches

# --- Environment Variables ---
# Ensure you have these set in your environment
# export PINECONE_API_KEY="YOUR_PINECONE_API_KEY"
# export OPENAI_API_KEY="YOUR_OPENAI_API_KEY"
load_dotenv()
pinecone_api_key = os.getenv("PINECONE_API_KEY")
openai_api_key = os.getenv("OPENAI_API_KEY")

if not pinecone_api_key:
    raise ValueError("PINECONE_API_KEY environment variable not set.")
if not openai_api_key:
    raise ValueError("OPENAI_API_KEY environment variable not set.")

# --- Initialize Clients ---
try:
    print("Initializing Pinecone client...")
    pc = Pinecone(api_key=pinecone_api_key)
    print("Initializing OpenAI client...")
    client = OpenAI(api_key=openai_api_key)
except Exception as e:
    print(f"Error initializing clients: {e}")
    exit(1)

# --- Get Embedding Function ---
def get_embedding(text, model=OPENAI_EMBEDDING_MODEL):
    """Generates an embedding for the given text using OpenAI API."""
    try:
        text = text.replace("\n", " ") # Recommended by OpenAI
        response = client.embeddings.create(input=[text], model=model)
        return response.data[0].embedding
    except Exception as e:
        print(f"Error getting embedding for text: '{text[:50]}...' - {e}")
        # Consider adding retry logic here if needed
        return None

# --- Ensure Pinecone Index Exists ---
def create_pinecone_index():
    """Checks if the index exists and creates it if not."""
    # The error "TypeError: argument of type 'method' is not iterable"
    # on the line checking `PINECONE_INDEX_NAME in pc.list_indexes().names`
    # suggests that `names` might be a method that needs calling `()`
    # rather than a direct attribute, potentially depending on the client version.
    try:
        # Get the list of index names
        index_list_object = pc.list_indexes()

        # Check if 'names' is an attribute (expected for recent versions)
        if hasattr(index_list_object, 'names'):
             # Check if names is callable (method) or an attribute (list)
             if callable(index_list_object.names):
                 # If it's callable, call it to get the list
                 list_of_index_names = index_list_object.names()
                 print("Using pc.list_indexes().names() method.")
             elif isinstance(index_list_object.names, list):
                 # If it's already a list attribute
                 list_of_index_names = index_list_object.names
                 print("Using pc.list_indexes().names attribute.")
             else:
                  raise TypeError(f"Unexpected type for pc.list_indexes().names: {type(index_list_object.names)}")
        # Fallback for older versions or unexpected structure where list_indexes() might return the list directly
        elif isinstance(index_list_object, list):
             list_of_index_names = index_list_object
             print("Using pc.list_indexes() directly as list (older client version?).")
        else:
             raise TypeError(f"Cannot determine index names from pc.list_indexes() result: {type(index_list_object)}")


        if PINECONE_INDEX_NAME not in list_of_index_names:
            print(f"Index '{PINECONE_INDEX_NAME}' not found. Creating...")
            try:
                pc.create_index(
                    name=PINECONE_INDEX_NAME,
                    dimension=EMBEDDING_DIMENSION,
                    metric="cosine",  # or "dotproduct", "euclidean"
                    spec=ServerlessSpec(
                        cloud=PINECONE_CLOUD,
                        region=PINECONE_REGION
                    )
                )
                # Wait for index to be ready
                while not pc.describe_index(PINECONE_INDEX_NAME).status['ready']:
                    print("Waiting for index to be ready...")
                    time.sleep(5)
                print(f"Index '{PINECONE_INDEX_NAME}' created successfully.")
            except Exception as e:
                print(f"Error creating index '{PINECONE_INDEX_NAME}': {e}")
                exit(1)
        else:
            print(f"Index '{PINECONE_INDEX_NAME}' already exists.")

    except Exception as e:
        print(f"Error during index check/creation: {e}")
        # Optional: Re-raise the exception if you want the script to stop more forcefully
        # raise e
        exit(1)


    # Connect to the index
    try:
        index = pc.Index(PINECONE_INDEX_NAME)
        print(f"Connected to index '{PINECONE_INDEX_NAME}'.")
        # Optional: Check index stats
        # print(index.describe_index_stats())
        return index
    except Exception as e:
        print(f"Error connecting to index '{PINECONE_INDEX_NAME}': {e}")
        exit(1)

# --- Process Meeting Transcripts ---
def process_meeting_transcripts(index):
    """Reads transcripts, chunks by meeting, generates embeddings, and upserts."""
    print(f"\nProcessing meeting transcripts from: {MEETING_TRANSCRIPTS_PATH}")
    try:
        with open(MEETING_TRANSCRIPTS_PATH, 'r', encoding='utf-8') as f:
            content = f.read()
    except FileNotFoundError:
        print(f"Error: File not found at {MEETING_TRANSCRIPTS_PATH}")
        return
    except Exception as e:
        print(f"Error reading file {MEETING_TRANSCRIPTS_PATH}: {e}")
        return

    # Split into meetings using the header format
    # Regex captures meeting number and date string
    meeting_headers = list(re.finditer(r"### Meeting (\d+): (.*?)\n", content))
    vectors_to_upsert = []

    print(f"Found {len(meeting_headers)} meetings.")

    for i, header_match in enumerate(tqdm(meeting_headers, desc="Processing Meetings")):
        meeting_number = int(header_match.group(1))
        date_str = header_match.group(2).strip()

        # Extract meeting content
        start_index = header_match.end()
        end_index = meeting_headers[i+1].start() if i + 1 < len(meeting_headers) else len(content)
        meeting_text = content[start_index:end_index].strip()

        if not meeting_text:
            print(f"Warning: Meeting {meeting_number} has no content. Skipping.")
            continue

        # Parse date string
        try:
            # Assuming format "Month Day, Year" e.g., "February 15, 2025"
            meeting_date_obj = datetime.strptime(date_str, "%B %d, %Y")
            meeting_date_iso = meeting_date_obj.strftime("%Y-%m-%d")
        except ValueError:
            print(f"Warning: Could not parse date '{date_str}' for meeting {meeting_number}. Skipping date metadata.")
            meeting_date_iso = None # Or handle as needed

        # Generate embedding
        embedding = get_embedding(meeting_text)
        if embedding is None:
            print(f"Skipping meeting {meeting_number} due to embedding error.")
            continue

        # Prepare metadata
        metadata = {
            "source": "meeting_transcript",
            "meeting_number": meeting_number,
            "text_snippet": meeting_text[:200] + "..." # Add a snippet for context
        }
        if meeting_date_iso:
            metadata["meeting_date"] = meeting_date_iso

        # Prepare vector for upsert
        vector_id = f"meeting-{meeting_number}"
        vectors_to_upsert.append({
            "id": vector_id,
            "values": embedding,
            "metadata": metadata
        })

        # Upsert in batches
        if len(vectors_to_upsert) >= UPSERT_BATCH_SIZE:
            print(f"Upserting batch of {len(vectors_to_upsert)} meeting vectors...")
            try:
                index.upsert(vectors=vectors_to_upsert)
                vectors_to_upsert = [] # Clear batch
            except Exception as e:
                print(f"Error upserting meeting batch: {e}")
                # Decide how to handle failed batches (e.g., retry, log)


    # Upsert any remaining vectors
    if vectors_to_upsert:
        print(f"Upserting final batch of {len(vectors_to_upsert)} meeting vectors...")
        try:
            index.upsert(vectors=vectors_to_upsert)
        except Exception as e:
            print(f"Error upserting final meeting batch: {e}")

    print("Finished processing meeting transcripts.")

# --- Process Jira Tickets ---
def process_jira_tickets(index):
    """Reads Jira tickets, generates embeddings, and upserts."""
    print(f"\nProcessing Jira tickets from: {JIRA_TICKETS_PATH}")
    try:
        with open(JIRA_TICKETS_PATH, 'r', encoding='utf-8') as f:
            tickets = json.load(f)
    except FileNotFoundError:
        print(f"Error: File not found at {JIRA_TICKETS_PATH}")
        return
    except json.JSONDecodeError:
        print(f"Error: Could not decode JSON from {JIRA_TICKETS_PATH}")
        return
    except Exception as e:
        print(f"Error reading file {JIRA_TICKETS_PATH}: {e}")
        return

    vectors_to_upsert = []
    print(f"Found {len(tickets)} Jira tickets.")

    for ticket in tqdm(tickets, desc="Processing Jira Tickets"):
        try:
            ticket_id = ticket.get("key")
            fields = ticket.get("fields", {})
            summary = fields.get("summary", "")
            description = fields.get("description", "")
            status = fields.get("status", {}).get("name")
            assignee = fields.get("assignee", {}).get("displayName")
            reporter = fields.get("reporter", {}).get("displayName")
            created_str = fields.get("created") # e.g., "2025-02-10T10:23:54.000+0000"
            labels = fields.get("labels", [])

            if not ticket_id or not (summary or description):
                print(f"Warning: Skipping ticket due to missing ID, summary, or description: {ticket.get('id')}")
                continue

            # Combine relevant text fields for embedding
            text_to_embed = f"Summary: {summary}\nDescription: {description}"
            if labels:
                text_to_embed += f"\nLabels: {', '.join(labels)}"

            # Generate embedding
            embedding = get_embedding(text_to_embed)
            if embedding is None:
                print(f"Skipping ticket {ticket_id} due to embedding error.")
                continue

            # Parse created date
            created_date_iso = None
            if created_str:
                try:
                    # Parse ISO 8601 format, ignoring timezone for simplicity here
                    created_date_obj = datetime.fromisoformat(created_str.split('.')[0]) # Remove fractional seconds
                    created_date_iso = created_date_obj.strftime("%Y-%m-%d")
                except ValueError:
                    print(f"Warning: Could not parse date '{created_str}' for ticket {ticket_id}. Skipping date metadata.")


            # Prepare metadata
            metadata = {
                "source": "jira_ticket",
                "ticket_id": ticket_id,
                "summary": summary,
                "status": status,
                "assignee": assignee,
                "reporter": reporter,
                "labels": labels,
                "text_snippet": text_to_embed[:200] + "..."
            }
            if created_date_iso:
                metadata["created_date"] = created_date_iso

             # Add other relevant fields as needed, ensure they are JSON serializable

            # Prepare vector for upsert
            vector_id = f"jira-{ticket_id}"
            vectors_to_upsert.append({
                "id": vector_id,
                "values": embedding,
                "metadata": metadata
            })

            # Upsert in batches
            if len(vectors_to_upsert) >= UPSERT_BATCH_SIZE:
                print(f"Upserting batch of {len(vectors_to_upsert)} Jira ticket vectors...")
                try:
                    index.upsert(vectors=vectors_to_upsert)
                    vectors_to_upsert = [] # Clear batch
                except Exception as e:
                    print(f"Error upserting Jira batch: {e}")
                    # Decide how to handle failed batches

        except Exception as e:
            print(f"Error processing ticket {ticket.get('id', 'UNKNOWN')}: {e}")
            continue # Skip to the next ticket

    # Upsert any remaining vectors
    if vectors_to_upsert:
        print(f"Upserting final batch of {len(vectors_to_upsert)} Jira ticket vectors...")
        try:
            index.upsert(vectors=vectors_to_upsert)
        except Exception as e:
            print(f"Error upserting final Jira batch: {e}")

    print("Finished processing Jira tickets.")

# --- Main Execution ---
if __name__ == "__main__":
    pinecone_index = create_pinecone_index()

    if pinecone_index:
        process_meeting_transcripts(pinecone_index)
        process_jira_tickets(pinecone_index)

        print("\nScript finished.")
        # Optional: Print final index stats
        # try:
        #     print("\nFinal index stats:")
        #     print(pinecone_index.describe_index_stats())
        # except Exception as e:
        #      print(f"Could not fetch final index stats: {e}")

    else:
        print("Exiting due to Pinecone index connection issues.")
