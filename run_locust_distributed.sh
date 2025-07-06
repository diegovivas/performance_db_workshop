#!/bin/bash

# Check if database type is provided
if [ -z "$1" ]; then
    echo "Usage: $0 [postgres|scylla] [--web] [--users N] [--spawn-rate N] [--workers N] [--duration TIME]"
    echo "Example: $0 postgres"
    echo "Example: $0 postgres --web"
    echo "Example: $0 postgres --users 200 --spawn-rate 50 --workers 8 --duration 5m"
    echo "Example: $0 scylla --web --users 500 --duration 2m"
    echo ""
    echo "Default values:"
    echo "  --users: 100"
    echo "  --spawn-rate: 20"
    echo "  --workers: 4"
    echo "  --duration: 1m"
    exit 1
fi

DB_TYPE=$1
WEB_MODE=false

# Default parameters
USER_COUNT=100
SPAWN_RATE=20
TEST_DURATION="1m"
WORKER_COUNT=4

# Parse command line arguments
shift # Remove first argument (DB_TYPE)
while [[ $# -gt 0 ]]; do
    case $1 in
        --web)
            WEB_MODE=true
            echo "Web mode enabled - Locust will run with web interface"
            shift
            ;;
        --users)
            USER_COUNT="$2"
            echo "User count set to: $USER_COUNT"
            shift 2
            ;;
        --spawn-rate)
            SPAWN_RATE="$2"
            echo "Spawn rate set to: $SPAWN_RATE"
            shift 2
            ;;
        --workers)
            WORKER_COUNT="$2"
            echo "Worker count set to: $WORKER_COUNT"
            shift 2
            ;;
        --duration)
            TEST_DURATION="$2"
            echo "Test duration set to: $TEST_DURATION"
            shift 2
            ;;
        *)
            echo "Unknown parameter: $1"
            echo "Use --help or run without parameters to see usage"
            exit 1
            ;;
    esac
done

# Validate database type
if [[ "$DB_TYPE" != "postgres" && "$DB_TYPE" != "scylla" ]]; then
    echo "Error: Database type must be either 'postgres' or 'scylla'"
    exit 1
fi

# Validate numeric parameters
if ! [[ "$USER_COUNT" =~ ^[0-9]+$ ]]; then
    echo "Error: User count must be a positive integer"
    exit 1
fi

if ! [[ "$SPAWN_RATE" =~ ^[0-9]+$ ]]; then
    echo "Error: Spawn rate must be a positive integer"
    exit 1
fi

if ! [[ "$WORKER_COUNT" =~ ^[0-9]+$ ]]; then
    echo "Error: Worker count must be a positive integer"
    exit 1
fi

echo "=== Test Configuration ==="
echo "Database: $DB_TYPE"
echo "Users: $USER_COUNT"
echo "Spawn Rate: $SPAWN_RATE"
echo "Workers: $WORKER_COUNT"
echo "Duration: $TEST_DURATION"
echo "Web Mode: $WEB_MODE"
echo "========================="

# Create results directory
RESULTS_DIR="${USER_COUNT}_${TEST_DURATION}"
mkdir -p "$RESULTS_DIR"

# Set file names with improved naming convention
HTML_FILE="${DB_TYPE}_${USER_COUNT}_${TEST_DURATION}.html"
CSV_PREFIX="${DB_TYPE}_${USER_COUNT}_${TEST_DURATION}"

# Set Locust file based on database type
if [ "$DB_TYPE" == "postgres" ]; then
    LOCUST_FILE="locust_postgres.py"
    echo "Running PostgreSQL performance test..."
elif [ "$DB_TYPE" == "scylla" ]; then
    LOCUST_FILE="locust_scylla.py"
    echo "Running ScyllaDB performance test..."
fi

# Path to Locust binary (assuming virtual environment is activated)
LOCUST_PATH="locust"
MASTER_BIND_HOST="127.0.0.1"
MASTER_BIND_PORT=5557

# Check if virtual environment is activated
if [ -z "$VIRTUAL_ENV" ]; then
    echo "Warning: No virtual environment detected. Make sure you have activated your virtual environment."
    echo "Run: source venv/bin/activate"
fi

# Allow some time for processes to terminate
sleep 3

# Build Locust command based on mode
if [ "$WEB_MODE" = true ]; then
    # Web mode - run with web interface
    echo "Starting Locust master for $DB_TYPE in web mode..."
    echo "You can view real-time results at: http://localhost:8089"
    LOCUST_CMD="$LOCUST_PATH -f $LOCUST_FILE --master --master-bind-host=$MASTER_BIND_HOST --master-bind-port=$MASTER_BIND_PORT --html $RESULTS_DIR/$HTML_FILE --csv $RESULTS_DIR/$CSV_PREFIX"
else
    # Headless mode - run without web interface
    echo "Starting Locust master for $DB_TYPE in headless mode..."
    LOCUST_CMD="$LOCUST_PATH -f $LOCUST_FILE --master --master-bind-host=$MASTER_BIND_HOST --master-bind-port=$MASTER_BIND_PORT --headless -u $USER_COUNT -r $SPAWN_RATE -t $TEST_DURATION --html $RESULTS_DIR/$HTML_FILE --csv $RESULTS_DIR/$CSV_PREFIX"
fi

# Start the Locust master node
$LOCUST_CMD &

# Allow some time for the master to start
sleep 5

# Start the specified number of Locust workers to utilize all cores
echo "Starting $WORKER_COUNT Locust workers..."
for i in $(seq 1 $WORKER_COUNT); do
   $LOCUST_PATH -f $LOCUST_FILE --worker --master-host=$MASTER_BIND_HOST --master-port=$MASTER_BIND_PORT &
done

# Allow some time for all workers to start
sleep 5

echo "Locust is running in distributed mode with $WORKER_COUNT workers and a user limit of $USER_COUNT for $DB_TYPE."
if [ "$WEB_MODE" = true ]; then
    echo "Web interface available at: http://localhost:8089"
    echo "Configure your test parameters in the web interface and start the test."
else
    echo "Test will run for $TEST_DURATION in headless mode"
fi
echo "Results will be saved to $RESULTS_DIR/ directory:"
echo "  - HTML report: $RESULTS_DIR/$HTML_FILE"
echo "  - CSV reports: $RESULTS_DIR/${CSV_PREFIX}_stats.csv, ${CSV_PREFIX}_failures.csv, ${CSV_PREFIX}_exceptions.csv"
