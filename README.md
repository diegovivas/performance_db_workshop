# Performance DB  Comparison

This project is a workshop for pycon Colombia 2025 and performs comprehensive load testing to compare the performance and scalability of PostgreSQL and ScyllaDB under high concurrency scenarios using Locust. The tests simulate an e-commerce platform with realistic order management operations.

## Features

- **CRUD Operations Testing**: Tests all four basic database operations:
  - **Create** (Insert data)
  - **Read** (Query data with various patterns)
  - **Update** (Modify existing records)
  - **Delete** (Remove records)

- **Containerized Databases**: Uses Docker Compose to run local instances of PostgreSQL and ScyllaDB
- **Distributed Load Testing**: Supports multi-worker Locust execution for maximum performance
- **Automated Comparison**: Includes scripts to compare performance metrics between= databases

## Prerequisites

- Python 3.8 <= 3.12
- Docker and Docker Compose
- Git

## Setup


#### 1. Clone and Navigate to Project

```bash
git clone <repository-url>
cd performance_db_workshop
```

#### 2. Create and Activate Virtual Environment

```bash
# Create virtual environment
python3.9 -m venv venv 

# Activate virtual environment
source venv/bin/activate  # On macOS/Linux
# or
venv\Scripts\activate     # On Windows
```

#### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

#### 4. Setup Environment Variables

```bash
# Copy the example environment file
cp env.example .env

# The default values in env.example are configured for Docker containers
# No changes needed unless you want to modify ports or credentials
```

#### 5. Start Database Containers

```bash
# Start both PostgreSQL and ScyllaDB containers
docker-compose up -d

# Wait for containers to be ready (about 30-60 seconds)
docker-compose ps  # Check if containers are healthy
```

#### 6. Create Database Tables

```bash
# Create PostgreSQL table
python create_postgres_table.py

# Create ScyllaDB table
python create_scylla_table.py
```

## Running Performance Tests

### Single Database Tests

#### Test PostgreSQL:
```bash
# Simple test
locust -f locust_postgres.py --headless -u 100 -r 10 -t 5m

# Distributed test (recommended)
./run_locust_distributed.sh postgres
```

#### Test ScyllaDB:
```bash
# Simple test
locust -f locust_scylla.py --headless -u 100 -r 10 -t 5m

# Distributed test (recommended)
./run_locust_distributed.sh scylla
```

### Complete Comparison Workflow

```bash
# 1. Test PostgreSQL
./run_locust_distributed.sh postgres

# 2. Wait for test to complete, then test ScyllaDB
./run_locust_distributed.sh scylla

# 3. Compare results
python compare_results.py
```

## Test Parameters Explanation

- `-u 100`: Total number of concurrent users (connections)
- `-r 10`: Spawn rate (users started per second)
- `-t 5m`: Test duration (5 minutes)
- `--headless`: Run without web interface

### Distributed Test Default Parameters

- **Users**: 100 concurrent users (optimized for resource usage)
- **Spawn Rate**: 10 users/second
- **Duration**: 10 minutes
- **Workers**: 8 worker processes

You can modify these in `run_locust_distributed.sh`.

### Performance Optimizations

The project includes several optimizations for better performance:

#### PostgreSQL Defaults:
- **max_connections**: 300 
- **shared_buffers**: 512MB 
- **work_mem**: 8MB 
- **Connection pool**: 

#### ScyllaDB Defaults:
- **Memory**: 4GB 
- **CPU cores**: 2 



## Test Operations

Each test performs these e-commerce operations with different weights:

1. **Insert (Weight: 4)** - Creates new orders with realistic data:
   - Customer information and email
   - Order numbers and amounts
   - Payment methods and shipping addresses
   - Order status and timestamps
2. **Read (Weight: 3)** - Queries orders using various patterns:
   - By order status (pending, shipped, delivered, etc.)
   - By customer email
   - By user ID
   - By date range
   - By specific order ID
   - Recent orders sampling
3. **Update (Weight: 2)** - Modifies existing orders:
   - Change order status
   - Update total amounts
   - Update timestamps
4. **Delete (Weight: 1)** - Removes orders from database

## Results and Analysis

### Individual Results

After each test, Locust creates a new directory with the format `{users}_{duration}` (e.g., `100_1m`, `1000_5m`) containing CSV files:

**Directory Structure:**
```
100_1m/
├── postgres_100_1m_stats.csv      # PostgreSQL performance statistics
├── postgres_100_1m_failures.csv   # PostgreSQL failure details
├── postgres_100_1m_exceptions.csv # PostgreSQL exception details
├── postgres_100_1m_stats_history.csv # PostgreSQL time-series data
├── scylla_100_1m_stats.csv        # ScyllaDB performance statistics
├── scylla_100_1m_failures.csv     # ScyllaDB failure details
├── scylla_100_1m_exceptions.csv   # ScyllaDB exception details
└── scylla_100_1m_stats_history.csv # ScyllaDB time-series data
```

**CSV Files Generated:**
- `*_stats.csv` - Aggregated performance metrics (throughput, latency, errors)
- `*_failures.csv` - Detailed failure information
- `*_exceptions.csv` - Exception details and stack traces
- `*_stats_history.csv` - Time-series data for detailed analysis

### Automated Comparison

Run the comparison script to get a detailed analysis:

```bash
python db_comparison_report.py <results_directory>
```

**Example:**
```bash
# After running tests, analyze the results
python db_comparison_report.py 100_1m
```

This generates a comprehensive HTML report with:

#### 📊 **Performance Metrics Analyzed:**
- **Scalability (35% weight)**: User achievement rate - how many users the database actually handled
- **Throughput (25% weight)**: Requests per second - processing capacity
- **Latency (20% weight)**: Response times (avg, median, percentiles)
- **Reliability (15% weight)**: Error rates and failure handling
- **Consistency (5% weight)**: Performance variability over time

#### 📈 **Generated Reports:**
1. **HTML Report**: Complete analysis with charts and recommendations
2. **Performance Charts**: 
   - Throughput comparison bar chart
   - Latency percentiles comparison
   - Scalability (user achievement) comparison
   - Performance radar chart (multi-dimensional view)
3. **Console Summary**: Quick overview with key metrics

#### 🎯 **Smart Analysis Features:**
- **Automatic Database Discovery**: Finds all tested databases in the results directory
- **Weighted Scoring**: Combines multiple metrics into overall performance score
- **Scalability Reality Check**: Highlights when score winner ≠ scalability leader
- **Contextual Recommendations**: Provides specific advice based on results
- **Performance Gap Analysis**: Shows how much better the winner performs

#### 📋 **Sample Output:**
```
🏆 PERFORMANCE COMPARISON RESULTS:
============================================================
1. POSTGRES: 85.2/100
   Scalability: 95.0% (95,000 of 100,000 users)
   Throughput: 1,250.5 req/s
   Avg Latency: 45.23ms
   Failure Rate: 0.15%

2. SCYLLA: 78.9/100
   Scalability: 100.0% (100,000 of 100,000 users)
   Throughput: 1,180.2 req/s
   Avg Latency: 52.10ms
   Failure Rate: 0.08%

🥇 SCORE WINNER: POSTGRES with 85.2/100

🎯 SCALABILITY ANALYSIS:
============================================================
👥 Most Users Handled: SCYLLA (100,000 users - 100.0%)
⚡ Highest Throughput: POSTGRES (1,250.5 req/s)
📈 Most Total Work: POSTGRES (750,300 requests)
🎯 Best Efficiency: POSTGRES (13.16 req/s per user)

⚠️  IMPORTANT CONTEXT:
   POSTGRES won by SCORE but only handled 95.0% of target users
   SCYLLA handled 5% MORE USERS in practice!
   🏆 SCYLLA shows better REAL-WORLD SCALABILITY
```

### Advanced Analysis Options

#### Custom Weights
You can customize the importance of different metrics:

```bash
# Prioritize throughput over scalability
python db_comparison_report.py 100_1m --weights '{"throughput":0.4,"scalability":0.2,"latency":0.2,"reliability":0.15,"consistency":0.05}'

# Focus on reliability and consistency
python db_comparison_report.py 100_1m --weights '{"reliability":0.4,"consistency":0.3,"throughput":0.2,"latency":0.1}'
```

#### Understanding the Results Directory
The script expects results in directories named like `{users}_{duration}`:
- `100_1m` = 100 users, 1 minute test
- `1000_5m` = 1000 users, 5 minute test
- `10000_10m` = 10000 users, 10 minute test

#### Generated Files
After running the comparison, you'll find:
- `comparison_report.html` - Complete analysis report
- `throughput_comparison.png` - Throughput bar chart
- `latency_percentiles.png` - Latency comparison
- `scalability_comparison.png` - User achievement rates
- `performance_radar.png` - Multi-dimensional performance view

## Docker Container Management

```bash
# Start containers
docker compose up -d

# Stop containers
docker compose down

# View logs
docker compose logs postgres
docker compose logs scylla

# Reset data (removes all data)
docker compose down -v
docker compose up -d
```

## Troubleshooting

### Database Connection Issues

1. **Check containers are running**:
   ```bash
   docker-compose ps
   ```

2. **Wait for health checks**:
   ```bash
   # PostgreSQL should show "healthy"
   # ScyllaDB may take 1-2 minutes to be fully ready
   ```

3. **Check connectivity**:
   ```bash
   # Test PostgreSQL
   docker exec -it postgres_db psql -U testuser -d testdb -c "SELECT 1;"
   
   # Test ScyllaDB
   docker exec -it scylla_db cqlsh -e "DESCRIBE KEYSPACES;"
   ```

### Virtual Environment Issues

```bash
# Make sure virtual environment is activated
source venv/bin/activate

# Verify Locust is installed
which locust
locust --version
```

### Performance Issues

- **Increase Docker resources**: Allocate more CPU/memory to Docker
- **Adjust test parameters**: Reduce concurrent users or spawn rate
- **Monitor system resources**: Use `htop` or Activity Monitor

## Customization

### Modify Test Parameters

Edit `run_locust_distributed.sh`:
```bash
USER_COUNT=1000      # Total concurrent users
SPAWN_RATE=50        # Users spawned per second
TEST_DURATION="10m"  # Test duration
WORKER_COUNT=8       # Number of worker processes
```

### Modify Database Configuration

Edit `docker-compose.yml` to change:
- Port mappings
- Memory allocation
- Volume mounts
- Environment variables

### Modify Test Data

Edit the `_random_string()` and data generation methods in:
- `locust_postgres.py`
- `locust_scylla.py`

## Architecture

```
┌─────────────────┐    ┌─────────────────┐
│   PostgreSQL    │    │    ScyllaDB     │
│   (Port 5432)   │    │   (Port 9042)   │
└─────────────────┘    └─────────────────┘
         │                       │
         └───────────┬───────────┘
                     │
         ┌─────────────────┐
         │  Locust Tests   │
         │   (CRUD Ops)    │
         └─────────────────┘
                     │
         ┌─────────────────┐
         │ Results & Stats │
         │   Comparison    │
         └─────────────────┘
```

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test with both databases
5. Submit a pull request

## License

This project is for educational and benchmarking purposes.
