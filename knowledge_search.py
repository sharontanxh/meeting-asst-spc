import json
import os
from typing import Any, Dict, List, Optional, Union

import pinecone
from dotenv import load_dotenv
from openai import OpenAI
from pinecone import Pinecone

load_dotenv()

PINECONE_API_KEY = os.environ["PINECONE_API_KEY"]
PINECONE_ENVIRONMENT = os.environ["PINECONE_ENVIRONMENT"]
PINECONE_INDEX_HOST = os.environ["PINECONE_INDEX_HOST"]
OPENAI_EMBEDDING_MODEL = "text-embedding-3-small"

# Path to the meeting map JSON file
MEETING_MAP_PATH = os.path.join("data", "meeting_map.json")

openai_client = OpenAI()


class PineconeClient:
    def __init__(
        self,
        api_key: str,
        environment: str,
        index_host: str,
    ):
        """
        Initialize the Pinecone client.

        Args:
            api_key: Pinecone API key
            environment: Pinecone environment
            index_name: Name of the Pinecone index to query
        """
        self.api_key = api_key or PINECONE_API_KEY
        self.environment = environment or PINECONE_ENVIRONMENT
        self.index_host = index_host or PINECONE_INDEX_HOST

        if not all([self.api_key, self.environment, self.index_host]):
            raise ValueError(
                "Missing required Pinecone configuration. Please set PINECONE_API_KEY, PINECONE_ENVIRONMENT, and PINECONE_INDEX."
            )

        pc = Pinecone(api_key=self.api_key, environment=self.environment)
        self.index = pc.Index(host=self.index_host)

    def search(
        self,
        query_vector: List[float],
        top_k: int = 5,
        namespace: str = "",
        filter: Optional[Dict[str, Any]] = None,
        include_metadata: bool = True,
        include_values: bool = False,
    ) -> Dict[str, Any]:
        """
        Search the Pinecone index for similar vectors.

        Args:
            query_vector: The query vector to search for (list of floats)
            top_k: Number of results to return
            namespace: Namespace to search in
            filter: Metadata filters to apply to the search
            include_metadata: Whether to include metadata in the results
            include_values: Whether to include vector values in the results

        Returns:
            Dict containing search results with matches, including vector content and metadata if requested
        """
        try:
            query_params = {
                "vector": query_vector,
                "top_k": top_k,
                "include_metadata": include_metadata,
                "include_values": include_values,
            }

            # Add optional parameters if provided
            if namespace:
                query_params["namespace"] = namespace
            if filter:
                query_params["filter"] = filter

            # Execute the query
            results = self.index.query(
                vector=query_vector,
                top_k=top_k,
                include_metadata=include_metadata,
                include_values=include_values,
                namespace=namespace,
                filter=filter,
            )

            return {
                "success": True,
                "results": results,
            }

        except Exception as e:
            return {
                "success": False,
                "message": f"Error searching Pinecone: {str(e)}",
                "results": None,
            }


def search_pinecone(
    query_vector: List[float],
    api_key: str,
    environment: str,
    index_host: str,
    top_k: int = 5,
    namespace: str = "",
    filter: Optional[Dict[str, Any]] = None,
    include_metadata: bool = True,
    include_values: bool = False,
) -> Dict[str, Any]:
    """
    Search a Pinecone vector database and return vector content and metadata.

    Args:
        query_vector: The query vector to search for (list of floats)
        top_k: Number of results to return
        namespace: Namespace to search in
        filter: Metadata filters to apply to the search
        include_metadata: Whether to include metadata in the results
        include_values: Whether to include vector values in the results
        api_key: Pinecone API key (uses env var if not provided)
        environment: Pinecone environment (uses env var if not provided)
        index_name: Name of the Pinecone index to query (uses env var if not provided)

    Returns:
        Dict containing search results with matches, including vector content and metadata if requested
    """
    client = PineconeClient(api_key, environment, index_host)
    return client.search(
        query_vector=query_vector,
        top_k=top_k,
        namespace=namespace,
        filter=filter,
        include_metadata=include_metadata,
        include_values=include_values,
    )


def get_embedding(text, model=OPENAI_EMBEDDING_MODEL):
    """Generates an embedding for the given text using OpenAI API."""
    try:
        text = text.replace("\n", " ")  # Recommended by OpenAI
        response = openai_client.embeddings.create(input=[text], model=model)
        return response.data[0].embedding
    except Exception as e:
        print(f"Error getting embedding for text: '{text[:50]}...' - {e}")
        # Consider adding retry logic here if needed
        return None


def process_knowledge_search_results(raw_jira_results, raw_meeting_results, query):
    """
    Process and combine search results from Jira tickets and meeting transcripts.

    Args:
        raw_jira_results: The raw results from searching Jira tickets
        raw_meeting_results: The raw results from searching meeting transcripts
        query: The original search query

    Returns:
        A JSON string containing the combined search results
    """
    # Initialize results container
    all_results = []
    success = True
    error_message = ""

    # Load meeting map for transcript lookup
    meeting_map = {}
    try:
        if os.path.exists(MEETING_MAP_PATH):
            with open(MEETING_MAP_PATH, "r") as f:
                meeting_map = json.load(f)
    except Exception as e:
        error_message += f"Failed to load meeting map: {str(e)} "

    # Process Jira results
    if raw_jira_results.get("success", False):
        jira_matches = raw_jira_results.get("results", {}).get("matches", [])
        for match in jira_matches:
            metadata = match.get("metadata", {})

            # Add source type if not already present
            if "source_type" not in metadata:
                metadata["source_type"] = "jira_ticket"

            result = {
                "id": match.get("id", "unknown"),
                "score": match.get("score", 0),
                "metadata": metadata,
                "type": "jira",
            }
            all_results.append(result)
    else:
        # If Jira search failed, capture error but continue with meeting results
        success = raw_jira_results.get("success", False)
        error_message += raw_jira_results.get("message", "Jira search failed")

    # Process meeting transcript results
    if raw_meeting_results.get("success", False):
        meeting_matches = raw_meeting_results.get("results", {}).get("matches", [])
        for match in meeting_matches:
            metadata = match.get("metadata", {})
            meeting_id = match.get("id", "")

            # Add source type if not already present
            if "source_type" not in metadata:
                metadata["source_type"] = "meeting_transcript"

            # Add raw transcript text from meeting map if available
            if meeting_id in meeting_map:
                metadata["raw_text"] = meeting_map[meeting_id]

            result = {
                "id": meeting_id,
                "score": match.get("score", 0),
                "metadata": metadata,
                "type": "meeting",
            }
            all_results.append(result)
    else:
        # If meeting search failed, capture error
        if success:  # Only override success if it was true before
            success = raw_meeting_results.get("success", False)
        error_message += " " + raw_meeting_results.get(
            "message", "Meeting transcript search failed"
        )

    # Sort results by score (descending)
    all_results.sort(key=lambda x: x.get("score", 0), reverse=True)

    # Create the final response
    response = {
        "success": success,
        "query": query,
        "results_count": len(all_results),
        "results": all_results,
    }

    # Add error message if there was an error
    if error_message:
        response["message"] = error_message.strip()

    # Return as JSON string
    return json.dumps(response, indent=2)


def search_knowledge(query: str, top_k=3):
    """
    Search the knowledge base for information related to the query.
    Searches both Jira tickets and meeting transcripts and combines the results.

    Args:
        query: The search query text
        top_k: The number of top results to return for each source

    Returns:
        A JSON string containing the combined search results
    """
    vector = get_embedding(query)
    if vector is None:
        return json.dumps(
            {
                "success": False,
                "message": "Failed to generate embedding for query",
                "query": query,
                "results_count": 0,
                "results": [],
            }
        )

    # Search for Jira tickets
    raw_jira_results = search_pinecone(
        vector,
        PINECONE_API_KEY,
        PINECONE_ENVIRONMENT,
        PINECONE_INDEX_HOST,
        top_k=top_k,
        filter={"source": {"$eq": "jira_ticket"}},
    )

    # Search for meeting transcripts
    raw_meeting_results = search_pinecone(
        vector,
        PINECONE_API_KEY,
        PINECONE_ENVIRONMENT,
        PINECONE_INDEX_HOST,
        top_k=top_k,
        filter={"source": {"$eq": "meeting_transcript"}},
    )

    # Process and combine the results
    return process_knowledge_search_results(
        raw_jira_results, raw_meeting_results, query
    )


if __name__ == "__main__":
    # Example usage
    # This is just an example vector - replace with your actual vector

    # Test the search_knowledge function with a sample query
    test_query = "WiFi not working"
    print(f"Testing search_knowledge with query: '{test_query}'")

    # Call the search_knowledge function
    results_json = search_knowledge(test_query)

    # Parse the JSON to print in a more readable format
    results = json.loads(results_json)

    print(f"\nSearch successful: {results['success']}")
    print(f"Query: {results['query']}")
    print(f"Results count: {results['results_count']}")

    # Print the first few results
    if results["results_count"] > 0:
        print("\nTop results:")
        for i, result in enumerate(results["results"]):  # Show top 3 results
            print(f"\nResult {i+1} (Type: {result['type']}):")
            print(f"  ID: {result['id']}")
            print(f"  Score: {result['score']:.4f}")

            # Print key metadata fields
            metadata = result["metadata"]

            # Print metadata summary based on result type
            if result["type"] == "jira":
                if "summary" in metadata:
                    print(f"  Summary: {metadata['summary']}")
                elif "title" in metadata:
                    print(f"  Title: {metadata['title']}")

                if "status" in metadata:
                    print(f"  Status: {metadata['status']}")
                if "assignee" in metadata:
                    print(f"  Assignee: {metadata['assignee']}")
            elif result["type"] == "meeting":
                if "raw_text" in metadata:
                    # Print first 100 characters of raw text
                    raw_text = metadata["raw_text"]
                    print(f"  Raw Text: {raw_text}")

            # Print text snippet if available for either type
            if "text_snippet" in metadata:
                snippet = metadata["text_snippet"]
                print(f"  Snippet: {snippet}")
    else:
        print("No results found.")
