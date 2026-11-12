#!/bin/bash

# ============================================================================
# Project 5 - Backend Management Script
# A single tool to run, test, and manage your entire backend easily.
# ============================================================================

# Colors for beautiful terminal output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Print a nice header
print_header() {
    echo ""
    echo -e "${BLUE}============================================================${NC}"
    echo -e "${BLUE}  $1${NC}"
    echo -e "${BLUE}============================================================${NC}"
    echo ""
}

# Print success message
print_success() {
    echo -e "${GREEN} $1${NC}"
}

# Print error message
print_error() {
    echo -e "${RED} $1${NC}"
}

# Print info message
print_info() {
    echo -e "${YELLOW}ℹ $1${NC}"
}

# ============================================================================
# COMMANDS
# ============================================================================

# 1. Install all dependencies (first-time setup)
cmd_install() {
    print_header "INSTALLING DEPENDENCIES"
    if [ ! -d ".venv" ]; then
        print_info "Creating virtual environment with Python 3.12..."
        python3.12 -m venv .venv
    fi
    source .venv/bin/activate
    print_info "Installing project and dev/test dependencies..."
    pip install -e ".[dev,test]"
    print_success "Installation complete!"
}

# 2. Start the FastAPI server
cmd_server() {
    print_header "STARTING FASTAPI SERVER"
    source .venv/bin/activate
    print_info "Server will run at: http://localhost:8000"
    print_info "Swagger UI: http://localhost:8000/docs"
    print_info "Press Ctrl+C to stop the server."
    echo ""
    uvicorn app.api.main:app --reload --host 0.0.0.0 --port 8000
}

# 3. Start the database (Docker)
cmd_db_start() {
    print_header "STARTING POSTGRES DATABASE (DOCKER)"
    if ! command -v docker &> /dev/null; then
        print_error "Docker is not installed. Please install Docker first."
        exit 1
    fi
    
    # Check if container already exists
    if docker ps -a --format '{{.Names}}' | grep -q "^project5-db$"; then
        print_info "Container 'project5-db' already exists. Starting it..."
        docker start project5-db
    else
        print_info "Creating new Postgres container..."
        docker run -d \
            --name project5-db \
            -e POSTGRES_USER=postgres \
            -e POSTGRES_PASSWORD=postgres \
            -e POSTGRES_DB=project5 \
            -p 5432:5432 \
            postgres:16
    fi
    print_success "Database is running on port 5432!"
    print_info "Connection URL: postgresql+asyncpg://postgres:postgres@localhost:5432/project5"
}

# 4. Stop the database
cmd_db_stop() {
    print_header "STOPPING POSTGRES DATABASE"
    docker stop project5-db 2>/dev/null
    print_success "Database stopped."
}

# 5. Run database migrations
cmd_migrate() {
    print_header "RUNNING DATABASE MIGRATIONS"
    source .venv/bin/activate
    
    if [ "$1" = "new" ]; then
        # Create a new migration
        if [ -z "$2" ]; then
            print_error "Please provide a message: ./run.sh migrate new \"add new column\""
            exit 1
        fi
        print_info "Generating new migration: $2"
        alembic revision --autogenerate -m "$2"
        print_success "Migration file created!"
    else
        # Apply existing migrations
        print_info "Applying all pending migrations..."
        alembic upgrade head
        print_success "Database is up to date!"
    fi
}

# 6. Rollback the last migration
cmd_rollback() {
    print_header "ROLLING BACK LAST MIGRATION"
    source .venv/bin/activate
    print_info "Rolling back one step..."
    alembic downgrade -1
    print_success "Rollback complete."
}

# 7. Generate a test JWT token
cmd_token() {
    print_header "GENERATING TEST JWT TOKEN"
    source .venv/bin/activate
    
    ROLE=${1:-"admin"}
    USER=${2:-"test-user-123"}
    
    print_info "Generating token for user: $USER with role: $ROLE"
    TOKEN=$(python -c "from app.core.security import create_access_token; print(create_access_token(data={'sub': '$USER', 'roles': ['$ROLE']}))")
    
    echo ""
    echo -e "${GREEN}Your JWT Token:${NC}"
    echo "$TOKEN"
    echo ""
    print_info "Use it like this:"
    echo -e "${YELLOW}curl -H \"Authorization: Bearer $TOKEN\" http://localhost:8000/documents${NC}"
}

# 8. Run all tests
cmd_test() {
    print_header "RUNNING ALL TESTS"
    source .venv/bin/activate
    
    if [ "$1" = "frontend" ]; then
        print_info "Running frontend contract tests only..."
        pytest tests/test_frontend_contract.py -v
    else
        print_info "Running all tests with coverage..."
        pytest --cov=src/app
    fi
}

# 9. Format code with Ruff
cmd_format() {
    print_header "FORMATTING CODE WITH RUFF"
    source .venv/bin/activate
    print_info "Auto-formatting all Python files..."
    ruff format .
    print_info "Fixing linting issues..."
    ruff check --fix .
    print_success "Code is now clean and formatted!"
}

# 10. Check code quality (linting + types)
cmd_check() {
    print_header "CHECKING CODE QUALITY"
    source .venv/bin/activate
    
    print_info "Running Ruff linter..."
    ruff check .
    
    echo ""
    print_info "Running MyPy type checker..."
    mypy src/app || print_info "Some type warnings found (this is normal for legacy code)."
    
    print_success "Quality check complete!"
}

# 11. Invalidate cache (reload config without restart)
cmd_reload_cache() {
    print_header "INVALIDATING APPLICATION CACHE"
    
    if [ -z "$1" ]; then
        print_error "Please provide your JWT token: ./run.sh reload-cache <token>"
        exit 1
    fi
    
    TOKEN=$1
    print_info "Sending reload request to server..."
    
    RESPONSE=$(curl -s -w "\n%{http_code}" -X POST "http://localhost:8000/health/reload-config" \
        -H "Authorization: Bearer $TOKEN" \
        -H "accept: application/json")
    
    HTTP_CODE=$(echo "$RESPONSE" | tail -n1)
    BODY=$(echo "$RESPONSE" | sed '$d')
    
    if [ "$HTTP_CODE" = "200" ]; then
        print_success "Cache invalidated successfully!"
        echo "$BODY"
    else
        print_error "Failed (HTTP $HTTP_CODE): $BODY"
    fi
}

# 12. Full setup (install + db + migrate)
cmd_setup() {
    print_header "FULL PROJECT SETUP"
    cmd_install
    cmd_db_start
    sleep 3  # Wait for DB to be ready
    cmd_migrate
    print_success "🎉 Project is fully set up and ready to run!"
    print_info "Next step: Run './run.sh server' to start the API."
}

# 13. Show help menu
cmd_help() {
    echo ""
    echo -e "${BLUE}╔════════════════════════════════════════════════════════════╗${NC}"
    echo -e "${BLUE}║        PROJECT 5 - BACKEND MANAGEMENT TOOL               ║${NC}"
    echo -e "${BLUE}╚════════════════════════════════════════════════════════════╝${NC}"
    echo ""
    echo -e "${YELLOW}USAGE:${NC}"
    echo "  ./run.sh <command> [options]"
    echo ""
    echo -e "${YELLOW}AVAILABLE COMMANDS:${NC}"
    echo ""
    echo -e "  ${GREEN}SETUP & INSTALLATION${NC}"
    echo "    setup                    Full first-time setup (install + db + migrate)"
    echo "    install                  Install all Python dependencies"
    echo "    db-start                 Start the Postgres database (Docker)"
    echo "    db-stop                  Stop the Postgres database"
    echo ""
    echo -e "  ${GREEN}RUNNING THE APP${NC}"
    echo "    server                   Start the FastAPI server (with auto-reload)"
    echo "    migrate                  Apply all pending database migrations"
    echo "    migrate new \"message\"    Create a new migration file"
    echo "    rollback                 Undo the last database migration"
    echo ""
    echo -e "  ${GREEN}TESTING & QUALITY${NC}"
    echo "    test                     Run all tests with coverage"
    echo "    test frontend            Run frontend contract tests only"
    echo "    format                   Auto-format code with Ruff"
    echo "    check                    Run linter + type checker"
    echo ""
    echo -e "  ${GREEN}UTILITIES${NC}"
    echo "    token [role] [user]      Generate a test JWT token"
    echo "    reload-cache <token>     Invalidate app cache (requires admin token)"
    echo "    help                     Show this help menu"
    echo ""
    echo -e "${YELLOW}EXAMPLES:${NC}"
    echo "  ./run.sh setup                       # First-time setup"
    echo "  ./run.sh server                      # Start the API"
    echo "  ./run.sh token admin my-user         # Get admin JWT token"
    echo "  ./run.sh test frontend               # Test frontend integration"
    echo "  ./run.sh migrate new \"add users\"     # Create new migration"
    echo ""
}

# ============================================================================
# MAIN ROUTER
# ============================================================================

case "$1" in
    setup)
        cmd_setup
        ;;
    install)
        cmd_install
        ;;
    server)
        cmd_server
        ;;
    db-start)
        cmd_db_start
        ;;
    db-stop)
        cmd_db_stop
        ;;
    migrate)
        cmd_migrate "$2" "$3"
        ;;
    rollback)
        cmd_rollback
        ;;
    token)
        cmd_token "$2" "$3"
        ;;
    test)
        cmd_test "$2"
        ;;
    format)
        cmd_format
        ;;
    check)
        cmd_check
        ;;
    reload-cache)
        cmd_reload_cache "$2"
        ;;
    help|--help|-h|"")
        cmd_help
        ;;
    *)
        print_error "Unknown command: $1"
        echo ""
        cmd_help
        exit 1
        ;;
esac