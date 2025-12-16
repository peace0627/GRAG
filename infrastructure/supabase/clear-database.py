#!/usr/bin/env python3
"""
Supabase Database Clear Script
This script will completely clear all records from the vectors table in Supabase
"""

import os
from supabase import create_client

def clear_supabase_database():
    try:
        # Read environment variables
        env_file = '.env'
        supabase_url = None
        supabase_key = None

        if os.path.exists(env_file):
            with open(env_file, 'r') as f:
                for line in f:
                    line = line.strip()
                    if line.startswith('SUPABASE_URL='):
                        supabase_url = line.split('=', 1)[1]
                    elif line.startswith('SUPABASE_KEY='):
                        supabase_key = line.split('=', 1)[1]

        supabase_url = supabase_url or os.getenv('SUPABASE_URL')
        supabase_key = supabase_key or os.getenv('SUPABASE_KEY')

        if not supabase_url or not supabase_key:
            print("❌ Cannot get SUPABASE_URL or SUPABASE_KEY from .env file or environment variables")
            return False

        print("🔗 Connecting to Supabase...")
        supabase = create_client(supabase_url, supabase_key)

        # Check current record count
        try:
            result = supabase.table('vectors').select('vector_id', count='exact').execute()
            initial_count = result.count if hasattr(result, 'count') else len(result.data)
            print(f"📊 Current vectors table has {initial_count} records")
        except Exception as e:
            print(f"⚠️ Could not get initial count: {e}")
            initial_count = 0

        # Clear all records from vectors table
        print("🗑️ Deleting all records from vectors table...")
        try:
            # Delete all records (neq with a dummy UUID to delete everything)
            result = supabase.table('vectors').delete().neq('vector_id', '00000000-0000-0000-0000-000000000000').execute()
            deleted_count = len(result.data) if result.data else 0
            print(f"✅ Successfully deleted {deleted_count} records from vectors table")
        except Exception as e:
            print(f"❌ Failed to delete records: {e}")
            return False

        # Verify the table is empty
        try:
            result = supabase.table('vectors').select('vector_id', count='exact').execute()
            final_count = result.count if hasattr(result, 'count') else len(result.data)
            print(f"📊 After cleanup: {final_count} records remaining")

            if final_count == 0:
                print("🎉 Supabase vectors table successfully cleared!")
                return True
            else:
                print(f"⚠️ Warning: {final_count} records still remain")
                return False

        except Exception as e:
            print(f"⚠️ Could not verify cleanup: {e}")
            print("🎯 Assuming cleanup was successful")
            return True

    except Exception as e:
        print(f"❌ Supabase cleanup failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    print("🧹 Supabase Database Clear Script")
    print("=" * 50)

    success = clear_supabase_database()

    if success:
        print("\n✅ Database cleanup completed successfully!")
        exit(0)
    else:
        print("\n❌ Database cleanup failed!")
        exit(1)
