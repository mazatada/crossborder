import random
from typing import Dict, Any, List

class UltraciteClient:
    """Interface for Ultracite Client."""
    def search(self, query: str) -> str:
        raise NotImplementedError

class MockUltraciteClient(UltraciteClient):
    """Mock implementation of Ultracite Client for testing/dev environments."""
    
    def search(self, query: str) -> str:
        """
        Returns a mock search result.
        In a real scenario, this would call the Ultracite API.
        For now, we return a static string with a timestamp or random element 
        to simulate potential changes if needed, or stable data.
        """
        # Return stable data by default to avoid noise, 
        # but we can inject changes in tests if needed.
        return f"Mock result for query: {query}\n\n- Regulation A: Valid\n- Regulation B: Valid"

    def search_with_variation(self, query: str) -> str:
        """Helper to simulate a change in regulations."""
        return f"Mock result for query: {query}\n\n- Regulation A: Valid\n- Regulation B: UPDATED (New Requirement)"
