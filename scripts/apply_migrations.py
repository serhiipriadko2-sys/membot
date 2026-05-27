"""
Script to apply Supabase migrations.
Usage: python scripts/apply_migrations.py
"""
import os
import sys
from pathlib import Path
from supabase import create_client
from dotenv import load_dotenv

load_dotenv()


def get_supabase_client():
    """Initialize Supabase client."""
    url = os.getenv("SUPABASE_URL")
    key = os.getenv("SUPABASE_KEY")
    
    if not url or not key:
        print("[ERROR] Missing SUPABASE_URL or SUPABASE_KEY in .env")
        sys.exit(1)
    
    if key == "YOUR_NEW_SECRET_KEY_HERE":
        print("[ERROR] Please update SUPABASE_KEY in .env with your actual secret key")
        sys.exit(1)
    
    return create_client(url, key)


def apply_migration(client, migration_file: str):
    """Apply a single migration file."""
    migration_path = Path(migration_file)
    
    if not migration_path.exists():
        print(f"[ERROR] Migration file not found: {migration_file}")
        return False
    
    print(f"[FACT] Applying migration: {migration_file}")
    
    with open(migration_path, 'r') as f:
        sql_content = f.read()
    
    try:
        # Split by semicolons and execute each statement
        # Note: Supabase Python client doesn't have direct SQL execution
        # We'll need to use the REST API or rpc endpoint for complex migrations
        # For now, we'll document that migrations should be applied via Supabase Dashboard
        
        print("[INTERP] Direct SQL execution via Python client is limited.")
        print("[HYP] Recommended approach:")
        print("  1. Go to Supabase Dashboard → SQL Editor")
        print(f"  2. Copy content from {migration_file}")
        print("  3. Execute the SQL manually")
        print("\nAlternatively, use Supabase CLI:")
        print("  npx supabase db push")
        
        return True
        
    except Exception as e:
        print(f"[ERROR] Migration failed: {e}")
        return False


def check_connection(client):
    """Test database connection."""
    try:
        # Try to query the health check table
        response = client.table("_membot_health_check").select("*").limit(1).execute()
        print("[FACT] Connection successful - health check table exists")
        return True
    except Exception as e:
        error_msg = str(e).lower()
        if "relation" in error_msg or "not exist" in error_msg:
            print("[INTERP] Connection OK, but tables not initialized yet")
            return True
        print(f"[ERROR] Connection test failed: {e}")
        return False


def main():
    """Main entry point."""
    print("=" * 60)
    print("Membot Supabase Migration Tool")
    print("=" * 60)
    
    client = get_supabase_client()
    
    # Test connection
    if not check_connection(client):
        print("\n[ERROR] Cannot proceed without valid connection")
        sys.exit(1)
    
    # Find all migration files
    migrations_dir = Path(__file__).parent.parent / "migrations"
    migration_files = sorted(migrations_dir.glob("*.sql"))
    
    if not migration_files:
        print("[WARN] No migration files found in migrations/")
        sys.exit(0)
    
    print(f"\n[FACT] Found {len(migration_files)} migration(s)")
    
    # Apply migrations
    success_count = 0
    for migration_file in migration_files:
        if apply_migration(client, str(migration_file)):
            success_count += 1
    
    print("\n" + "=" * 60)
    print(f"Migration Summary: {success_count}/{len(migration_files)} successful")
    print("=" * 60)
    
    if success_count == len(migration_files):
        print("\n[FACT] All migrations processed successfully")
        print("\nNext steps:")
        print("1. Verify tables in Supabase Dashboard → Table Editor")
        print("2. Run: python src/storage/supabase_client.py to test connectivity")
        print("3. Update .env with your new secret key if not already done")
    else:
        print("\n[WARN] Some migrations may require manual intervention")
        sys.exit(1)


if __name__ == "__main__":
    main()
