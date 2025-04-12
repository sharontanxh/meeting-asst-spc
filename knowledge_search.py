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


def search_knowledge(query: str, top_k=3):
    vector = get_embedding(query)
    assert vector is not None
    return search_pinecone(
        vector, PINECONE_API_KEY, PINECONE_ENVIRONMENT, PINECONE_INDEX_HOST, top_k=top_k
    )


if __name__ == "__main__":
    # Example usage
    # This is just an example vector - replace with your actual vector
    example_vector = get_embedding("Wifi is not working")
    assert example_vector is not None

    print("Searching Pinecone...")
    results = search_pinecone(
        query_vector=example_vector,
        api_key=PINECONE_API_KEY,
        environment=PINECONE_ENVIRONMENT,
        index_host=PINECONE_INDEX_HOST,
        top_k=3,
        include_values=True,
    )

    if results["success"]:
        print(f"Found {len(results['results']['matches'])} matches:")
        for i, match in enumerate(results["results"]["matches"]):
            print(f"\nMatch {i+1}:")
            print(f"ID: {match['id']}")
            print(f"Score: {match['score']}")
            if "metadata" in match:
                print(f"Metadata: {match['metadata']}")
    else:
        print(f"Error: {results['message']}")
