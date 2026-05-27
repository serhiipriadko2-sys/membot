"""
Supabase Client Module for membot.
Provides centralized database connectivity and operations.
"""
import os
from supabase import create_client, Client
from dotenv import load_dotenv
from pydantic_settings import BaseSettings
from typing import Optional, List, Dict, Any
from datetime import datetime

load_dotenv()


class SupabaseConfig(BaseSettings):
    """Configuration for Supabase connection."""
    url: str
    key: str
    project_ref: str

    class Config:
        env_file = ".env"


class SupabaseClient:
    """Wrapper around Supabase client with membot-specific operations."""
    
    def __init__(self):
        self.config = SupabaseConfig()
        self.client: Optional[Client] = None
        self._connect()
    
    def _connect(self):
        """Initialize Supabase client connection."""
        try:
            self.client = create_client(self.config.url, self.config.key)
            print(f"[FACT] Connected to Supabase project: {self.config.project_ref}")
        except Exception as e:
            print(f"[ERROR] Failed to connect to Supabase: {e}")
            raise
    
    def test_connection(self) -> bool:
        """Test database connectivity."""
        try:
            # Try to fetch from a system table to verify connection
            response = self.client.table("_membot_health_check").select("*").limit(1).execute()
            return True
        except Exception as e:
            # Table might not exist yet, that's okay for connection test
            if "relation" in str(e).lower() or "not exist" in str(e).lower():
                print(f"[INTERP] Connection OK, but tables not initialized yet")
                return True
            print(f"[ERROR] Connection test failed: {e}")
            return False
    
    def create_health_check_table(self):
        """Create initial health check table via RPC or direct SQL."""
        # Note: Table creation typically requires migration files
        # This is a placeholder for future migration integration
        print("[HYP] Table creation should be done via Supabase migrations")
        return False
    
    def insert_hypothesis(self, hypothesis_id: str, name: str, 
                         probability: float, metadata: Dict[str, Any]) -> str:
        """Insert or update a hypothesis record."""
        try:
            data = {
                "hypothesis_id": hypothesis_id,
                "name": name,
                "probability": probability,
                "metadata": metadata,
                "updated_at": datetime.utcnow().isoformat()
            }
            
            response = self.client.table("membot_hypotheses").upsert(data).execute()
            print(f"[FACT] Hypothesis {hypothesis_id} saved/updated")
            return response.data[0]['id'] if response.data else None
        except Exception as e:
            print(f"[ERROR] Failed to save hypothesis: {e}")
            return None
    
    def get_hypotheses(self, limit: int = 100) -> List[Dict[str, Any]]:
        """Retrieve hypotheses from database."""
        try:
            response = self.client.table("membot_hypotheses")\
                .select("*")\
                .order("updated_at", desc=True)\
                .limit(limit)\
                .execute()
            return response.data if response.data else []
        except Exception as e:
            print(f"[ERROR] Failed to fetch hypotheses: {e}")
            return []
    
    def insert_event(self, event_type: str, payload: Dict[str, Any], 
                    source: str = "membot") -> Optional[str]:
        """Log an event to the database."""
        try:
            data = {
                "event_type": event_type,
                "payload": payload,
                "source": source,
                "timestamp": datetime.utcnow().isoformat()
            }
            
            response = self.client.table("membot_events").insert(data).execute()
            return response.data[0]['id'] if response.data else None
        except Exception as e:
            print(f"[ERROR] Failed to log event: {e}")
            return None
    
    def get_recent_events(self, event_type: Optional[str] = None, 
                         limit: int = 50) -> List[Dict[str, Any]]:
        """Retrieve recent events, optionally filtered by type."""
        try:
            query = self.client.table("membot_events").select("*")
            
            if event_type:
                query = query.eq("event_type", event_type)
            
            response = query.order("timestamp", desc=True).limit(limit).execute()
            return response.data if response.data else []
        except Exception as e:
            print(f"[ERROR] Failed to fetch events: {e}")
            return []


# Singleton instance
_supabase_client: Optional[SupabaseClient] = None


def get_supabase_client() -> SupabaseClient:
    """Get or create the singleton Supabase client instance."""
    global _supabase_client
    if _supabase_client is None:
        _supabase_client = SupabaseClient()
    return _supabase_client


if __name__ == "__main__":
    # Test connection
    client = get_supabase_client()
    if client.test_connection():
        print("✓ Supabase connection successful")
    else:
        print("✗ Supabase connection failed")
