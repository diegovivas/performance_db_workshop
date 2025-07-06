# Database Performance Comparison Tool

This tool analyzes Locust performance test results and generates comprehensive comparison reports between different databases.

## Features

- **Automated Analysis**: Discovers and analyzes all database test results in a directory
- **Comprehensive Metrics**: Evaluates throughput, latency, reliability, and consistency
- **Interactive Charts**: Generates professional visualization charts
- **HTML Report**: Creates a detailed, professional HTML report with scores and rankings
- **Flexible Scoring**: Weighted scoring system with customizable weights

## Installation

Make sure you have the required dependencies installed:

```bash
pip install -r requirements.txt
```

## Usage

### Basic Usage

```bash
python db_comparison_report.py <results_directory>
```

Example:
```bash
python db_comparison_report.py 100_1m
```

### Advanced Usage with Custom Weights

```bash
python db_comparison_report.py 100_1m --weights '{"throughput":0.5,"latency":0.3,"reliability":0.2}'
```

## Directory Structure

The tool expects the following file structure in your results directory:

```
100_1m/
├── postgres_100_1m_stats.csv
├── postgres_100_1m_failures.csv
├── postgres_100_1m_exceptions.csv
├── postgres_100_1m_stats_history.csv
├── scylla_100_1m_stats.csv
├── scylla_100_1m_failures.csv
├── scylla_100_1m_exceptions.csv
└── scylla_100_1m_stats_history.csv
```

## Generated Output

The tool generates the following files in the results directory:

1. **comparison_report.html** - Main comprehensive report
2. **throughput_comparison.png** - Throughput comparison chart
3. **latency_percentiles.png** - Latency percentiles comparison
4. **performance_radar.png** - Overall performance radar chart

## Scoring Methodology

The tool uses a weighted scoring system:

- **Throughput (40%)**: Requests per second - Higher is better
- **Latency (30%)**: Average response time - Lower is better  
- **Reliability (20%)**: Failure rate - Lower is better
- **Consistency (10%)**: Performance variability - Lower is better

Each metric is normalized to a 0-100 scale and combined using the weighted formula to produce an overall score.

## Sample Output

```
🏆 PERFORMANCE COMPARISON RESULTS:
==================================================
1. POSTGRES: 90.0/100
   Throughput: 175.8 req/s
   Avg Latency: 2.00ms
   Failure Rate: 0.00%

2. SCYLLA: 44.8/100
   Throughput: 96.7 req/s
   Avg Latency: 11.96ms
   Failure Rate: 0.00%

🥇 WINNER: POSTGRES with 90.0/100
📊 Report generated: 100_1m/comparison_report.html
```

## Metrics Analyzed

### Throughput Metrics
- Total requests processed
- Requests per second
- Request distribution by operation type

### Latency Metrics
- Average response time
- Median response time
- Percentiles (50th, 90th, 95th, 99th)
- Min/Max response times

### Reliability Metrics
- Total failures
- Failure rate percentage
- Error types and frequencies

### Consistency Metrics
- Throughput variability (standard deviation)
- Coefficient of variation
- Performance stability over time

## Custom Weights

You can customize the importance of different metrics by providing custom weights:

```bash
# Example: Prioritize throughput over latency
python db_comparison_report.py 100_1m --weights '{"throughput":0.6,"latency":0.2,"reliability":0.15,"consistency":0.05}'
```

Weights must sum to 1.0 and include all four categories.

## Integration with Test Scripts

This tool is designed to work seamlessly with the `run_locust_distributed.sh` script:

1. Run your performance tests:
   ```bash
   ./run_locust_distributed.sh postgres --users 100 --duration 1m
   ./run_locust_distributed.sh scylla --users 100 --duration 1m
   ```

2. Analyze results:
   ```bash
   python db_comparison_report.py 100_1m
   ```

3. View the HTML report in your browser

## Troubleshooting

### Common Issues

1. **"No database test results found"**: Make sure your CSV files follow the expected naming convention
2. **Missing dependencies**: Run `pip install -r requirements.txt`
3. **Permission errors**: Ensure the script has write permissions in the results directory

### File Naming Convention

The tool expects files to follow this pattern:
- `{database_name}_{users}_{duration}_stats.csv`
- `{database_name}_{users}_{duration}_failures.csv`
- `{database_name}_{users}_{duration}_exceptions.csv`
- `{database_name}_{users}_{duration}_stats_history.csv`

## Support

For issues or questions, please check:
1. File naming conventions are correct
2. All required dependencies are installed
3. CSV files contain the expected column headers
4. Directory permissions allow file creation

## License

This tool is part of the ScyllaDB workshop project and is intended for educational and benchmarking purposes. 