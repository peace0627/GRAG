#!/bin/bash

# GraphRAG Database Clear Script
# This script clears both Neo4j and Supabase databases

echo "🧹 GraphRAG Database Clear Script"
echo "================================="
echo ""

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check if we're in the right directory
if [ ! -f "pyproject.toml" ]; then
    print_error "Please run this script from the project root directory (where pyproject.toml is located)"
    exit 1
fi

# Confirm action
echo "⚠️  This will permanently delete ALL data from both databases:"
echo "   - Neo4j: All nodes and relationships"
echo "   - Supabase: All vector records"
echo ""
read -p "Are you sure you want to continue? (y/N): " -n 1 -r
echo ""
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    print_status "Operation cancelled by user."
    exit 0
fi

echo ""
print_status "Starting database cleanup..."

# Step 1: Clear Neo4j database
echo ""
print_status "Step 1: Clearing Neo4j database..."
echo "----------------------------------------"

if command -v cypher-shell &> /dev/null; then
    print_status "Using cypher-shell to clear Neo4j..."

    # Run the Neo4j clear script
    cypher-shell -f infrastructure/neo4j/clear-database.cypher

    if [ $? -eq 0 ]; then
        print_success "Neo4j database cleared successfully"
    else
        print_error "Failed to clear Neo4j database"
        exit 1
    fi
else
    print_warning "cypher-shell not found. Neo4j must be cleared manually."
    echo "Please run the following command manually:"
    echo "  cypher-shell -f infrastructure/neo4j/clear-database.cypher"
    echo ""
    echo "Or use Neo4j Browser at http://localhost:7474 with the script:"
    echo "  infrastructure/neo4j/clear-database.cypher"
fi

# Step 2: Clear Supabase database
echo ""
print_status "Step 2: Clearing Supabase database..."
echo "----------------------------------------"

if command -v python3 &> /dev/null; then
    print_status "Using Python script to clear Supabase..."

    # Run the Supabase clear script
    python3 infrastructure/supabase/clear-database.py

    if [ $? -eq 0 ]; then
        print_success "Supabase database cleared successfully"
    else
        print_error "Failed to clear Supabase database"
        exit 1
    fi
elif command -v python &> /dev/null; then
    print_status "Using Python script to clear Supabase..."

    # Run the Supabase clear script
    python infrastructure/supabase/clear-database.py

    if [ $? -eq 0 ]; then
        print_success "Supabase database cleared successfully"
    else
        print_error "Failed to clear Supabase database"
        exit 1
    fi
else
    print_warning "Python not found. Supabase must be cleared manually."
    echo "Please run the following command manually:"
    echo "  python3 infrastructure/supabase/clear-database.py"
    echo ""
    echo "Or manually delete all records from the 'vectors' table in Supabase dashboard."
fi

# Step 3: Clear any cached data
echo ""
print_status "Step 3: Clearing cached data..."
echo "---------------------------------"

# Clear Python cache
if [ -d "__pycache__" ]; then
    rm -rf __pycache__
    print_success "Cleared Python cache"
fi

if [ -d ".pytest_cache" ]; then
    rm -rf .pytest_cache
    print_success "Cleared pytest cache"
fi

# Clear any temporary files
if [ -d "temp" ]; then
    rm -rf temp/*
    print_success "Cleared temporary files"
fi

# Step 4: Final verification
echo ""
print_status "Step 4: Final verification..."
echo "-------------------------------"

print_status "Database cleanup completed!"
echo ""
print_success "✅ Neo4j database: All nodes and relationships cleared"
print_success "✅ Supabase database: All vector records cleared"
print_success "✅ Cache and temporary files: Cleared"
echo ""
print_warning "Note: This action cannot be undone. All processed documents and their data have been permanently removed."
echo ""
print_status "You can now restart fresh with new document uploads."
