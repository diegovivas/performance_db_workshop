#!/usr/bin/env python3
"""
Database Performance Comparison Report Generator
Analyzes Locust CSV performance test results and generates comprehensive comparison reports.
"""

import os
import sys
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from pathlib import Path
import json
from datetime import datetime
import argparse
from typing import Dict, List, Tuple, Optional
import warnings
warnings.filterwarnings('ignore')

# Set style for better looking plots
plt.style.use('seaborn-v0_8')
sns.set_palette("husl")

class DatabaseComparator:
    def __init__(self, results_dir: str):
        """
        Initialize the Database Comparator
        
        Args:
            results_dir: Directory containing the test results (e.g., '100_1m')
        """
        self.results_dir = Path(results_dir)
        self.databases = {}
        self.comparison_data = {}
        self.report_path = self.results_dir / "comparison_report.html"
        
        # Performance weights for overall score calculation
        self.weights = {
            'scalability': 0.35,   # 35% - User achievement rate (critical for real-world performance)
            'throughput': 0.25,    # 25% - Requests per second
            'latency': 0.20,       # 20% - Response time
            'reliability': 0.15,   # 15% - Error rate
            'consistency': 0.05    # 5% - Performance variability
        }
        
    def discover_databases(self) -> List[str]:
        """
        Discover all databases that have test results in the directory
        
        Returns:
            List of database names found
        """
        db_names = set()
        
        for file in self.results_dir.glob("*_stats.csv"):
            # Extract database name from filename
            # Format: {db_name}_{users}_{duration}_stats.csv
            name_parts = file.stem.split('_')
            if len(name_parts) >= 3:
                db_name = name_parts[0]
                db_names.add(db_name)
        
        return sorted(list(db_names))
    
    def load_database_data(self, db_name: str) -> Dict:
        """
        Load all CSV files for a specific database
        
        Args:
            db_name: Name of the database
            
        Returns:
            Dictionary containing all loaded data
        """
        data = {}
        
        # Find the actual file pattern by looking for files with the db_name prefix
        pattern_files = list(self.results_dir.glob(f"{db_name}_*_stats.csv"))
        if pattern_files:
            # Extract the full pattern from the first matching file
            stats_file = pattern_files[0]
            base_name = stats_file.stem.replace('_stats', '')
            base_pattern = f"{base_name}_"
        else:
            # Fallback to simple pattern
            base_pattern = f"{db_name}_"
        
        # Load stats file
        stats_file = self.results_dir / f"{base_pattern}stats.csv"
        if stats_file.exists():
            data['stats'] = pd.read_csv(stats_file)
        
        # Load failures file
        failures_file = self.results_dir / f"{base_pattern}failures.csv"
        if failures_file.exists():
            data['failures'] = pd.read_csv(failures_file)
        
        # Load exceptions file
        exceptions_file = self.results_dir / f"{base_pattern}exceptions.csv"
        if exceptions_file.exists():
            data['exceptions'] = pd.read_csv(exceptions_file)
        
        # Load history file
        history_file = self.results_dir / f"{base_pattern}stats_history.csv"
        if history_file.exists():
            data['history'] = pd.read_csv(history_file)
        
        return data
    
    def calculate_performance_metrics(self, db_name: str, data: Dict) -> Dict:
        """
        Calculate comprehensive performance metrics for a database
        
        Args:
            db_name: Database name
            data: Raw data dictionary
            
        Returns:
            Dictionary with calculated metrics
        """
        metrics = {'database': db_name}
        
        # Extract target user count from directory name (e.g., "100000_1m" -> 100000)
        try:
            target_users = int(self.results_dir.name.split('_')[0])
            metrics['target_users'] = target_users
        except (ValueError, IndexError):
            metrics['target_users'] = 0
        
        # Calculate actual max users reached from history
        metrics['max_users_reached'] = 0
        if 'history' in data and not data['history'].empty:
            history = data['history']
            if 'User Count' in history.columns:
                metrics['max_users_reached'] = history['User Count'].max()
        
        # Calculate user achievement rate (scalability metric)
        if metrics['target_users'] > 0:
            metrics['user_achievement_rate'] = (metrics['max_users_reached'] / metrics['target_users']) * 100
        else:
            metrics['user_achievement_rate'] = 0
        
        if 'stats' in data and not data['stats'].empty:
            stats = data['stats']
            
            # Get aggregated row (usually the last row)
            agg_row = stats[stats['Name'] == 'Aggregated'].iloc[-1] if not stats[stats['Name'] == 'Aggregated'].empty else stats.iloc[-1]
            
            # Throughput metrics
            metrics['total_requests'] = agg_row['Request Count']
            metrics['requests_per_sec'] = agg_row['Requests/s']
            
            # Latency metrics
            metrics['avg_response_time'] = agg_row['Average Response Time']
            metrics['median_response_time'] = agg_row['Median Response Time']
            metrics['min_response_time'] = agg_row['Min Response Time']
            metrics['max_response_time'] = agg_row['Max Response Time']
            
            # Percentile metrics
            metrics['p50'] = agg_row['50%']
            metrics['p90'] = agg_row['90%']
            metrics['p95'] = agg_row['95%']
            metrics['p99'] = agg_row['99%']
            
            # Reliability metrics
            metrics['total_failures'] = agg_row['Failure Count']
            metrics['failure_rate'] = (agg_row['Failure Count'] / agg_row['Request Count']) * 100 if agg_row['Request Count'] > 0 else 0
            
            # Adjusted throughput per user (efficiency metric)
            if metrics['max_users_reached'] > 0:
                metrics['throughput_per_user'] = metrics['requests_per_sec'] / metrics['max_users_reached']
            else:
                metrics['throughput_per_user'] = 0
        else:
            # Default values if no stats data
            metrics['total_requests'] = 0
            metrics['requests_per_sec'] = 0
            metrics['avg_response_time'] = 0
            metrics['median_response_time'] = 0
            metrics['min_response_time'] = 0
            metrics['max_response_time'] = 0
            metrics['p50'] = 0
            metrics['p90'] = 0
            metrics['p95'] = 0
            metrics['p99'] = 0
            metrics['total_failures'] = 0
            metrics['failure_rate'] = 0
            metrics['throughput_per_user'] = 0
            
        # Consistency metrics from history
        if 'history' in data and not data['history'].empty:
            history = data['history']
            history = history[history['Requests/s'] > 0]  # Filter out zero values
            
            if not history.empty:
                metrics['throughput_std'] = history['Requests/s'].std()
                metrics['throughput_cv'] = metrics['throughput_std'] / history['Requests/s'].mean() if history['Requests/s'].mean() > 0 else 0
                metrics['latency_std'] = history['Total Average Response Time'].std()
            else:
                metrics['throughput_std'] = 0
                metrics['throughput_cv'] = 0
                metrics['latency_std'] = 0
        else:
            metrics['throughput_std'] = 0
            metrics['throughput_cv'] = 0
            metrics['latency_std'] = 0
        
        return metrics
    
    def calculate_performance_scores(self, all_metrics: List[Dict]) -> List[Dict]:
        """
        Calculate normalized performance scores for comparison
        
        Args:
            all_metrics: List of metrics for all databases
            
        Returns:
            List of metrics with performance scores added
        """
        if not all_metrics:
            return all_metrics
        
        # Extract values for normalization
        scalability_values = [m['user_achievement_rate'] for m in all_metrics]
        throughput_values = [m['requests_per_sec'] for m in all_metrics]
        latency_values = [m['avg_response_time'] for m in all_metrics]
        failure_rates = [m['failure_rate'] for m in all_metrics]
        cv_values = [m.get('throughput_cv', 0) for m in all_metrics]
        
        # Normalize metrics (0-100 scale)
        max_scalability = max(scalability_values) if scalability_values else 1
        max_throughput = max(throughput_values) if throughput_values else 1
        min_latency = min(latency_values) if latency_values else 1
        max_failure_rate = max(failure_rates) if failure_rates else 1
        max_cv = max(cv_values) if cv_values else 1
        
        for metrics in all_metrics:
            # Higher is better for scalability (user achievement rate)
            metrics['scalability_score'] = (metrics['user_achievement_rate'] / max_scalability) * 100 if max_scalability > 0 else 0
            
            # Higher is better for throughput
            metrics['throughput_score'] = (metrics['requests_per_sec'] / max_throughput) * 100
            
            # Lower is better for latency (invert the score)
            metrics['latency_score'] = (1 - (metrics['avg_response_time'] - min_latency) / (max(latency_values) - min_latency)) * 100 if max(latency_values) > min_latency else 100
            
            # Lower is better for failure rate
            metrics['reliability_score'] = (1 - (metrics['failure_rate'] / max_failure_rate)) * 100 if max_failure_rate > 0 else 100
            
            # Lower is better for consistency (coefficient of variation)
            metrics['consistency_score'] = (1 - (metrics.get('throughput_cv', 0) / max_cv)) * 100 if max_cv > 0 else 100
            
            # Calculate overall score
            metrics['overall_score'] = (
                metrics['scalability_score'] * self.weights['scalability'] +
                metrics['throughput_score'] * self.weights['throughput'] +
                metrics['latency_score'] * self.weights['latency'] +
                metrics['reliability_score'] * self.weights['reliability'] +
                metrics['consistency_score'] * self.weights['consistency']
            )
        
        return all_metrics
    
    def generate_comparison_charts(self, all_metrics: List[Dict]) -> Dict[str, str]:
        """
        Generate comparison charts and return their file paths
        
        Args:
            all_metrics: List of metrics for all databases
            
        Returns:
            Dictionary with chart names and file paths
        """
        chart_files = {}
        
        if not all_metrics:
            return chart_files
        
        # Set up the plotting style
        plt.rcParams['figure.figsize'] = (12, 8)
        
        # 1. Throughput Comparison
        plt.figure(figsize=(10, 6))
        databases = [m['database'] for m in all_metrics]
        throughput = [m['requests_per_sec'] for m in all_metrics]
        
        bars = plt.bar(databases, throughput, color=sns.color_palette("husl", len(databases)))
        plt.title('Throughput Comparison (Requests/Second)', fontsize=16, fontweight='bold')
        plt.ylabel('Requests per Second', fontsize=12)
        plt.xlabel('Database', fontsize=12)
        
        # Add value labels on bars
        for bar, value in zip(bars, throughput):
            plt.text(bar.get_x() + bar.get_width()/2, bar.get_height() + max(throughput)*0.01, 
                    f'{value:.1f}', ha='center', va='bottom', fontweight='bold')
        
        plt.tight_layout()
        throughput_file = self.results_dir / "throughput_comparison.png"
        plt.savefig(throughput_file, dpi=300, bbox_inches='tight')
        plt.close()
        chart_files['throughput'] = throughput_file
        
        # 2. Latency Percentiles Comparison
        plt.figure(figsize=(12, 6))
        percentiles = ['p50', 'p90', 'p95', 'p99']
        x = np.arange(len(percentiles))
        width = 0.35
        
        for i, metrics in enumerate(all_metrics):
            values = [metrics[p] for p in percentiles]
            plt.bar(x + i * width, values, width, label=metrics['database'], alpha=0.8)
        
        plt.title('Latency Percentiles Comparison', fontsize=16, fontweight='bold')
        plt.ylabel('Response Time (ms)', fontsize=12)
        plt.xlabel('Percentile', fontsize=12)
        plt.xticks(x + width/2, ['50th', '90th', '95th', '99th'])
        plt.legend()
        plt.tight_layout()
        
        latency_file = self.results_dir / "latency_percentiles.png"
        plt.savefig(latency_file, dpi=300, bbox_inches='tight')
        plt.close()
        chart_files['latency'] = latency_file
        
        # 3. Scalability Comparison
        plt.figure(figsize=(10, 6))
        scalability_rates = [m['user_achievement_rate'] for m in all_metrics]
        colors = sns.color_palette("husl", len(databases))
        
        bars = plt.bar(databases, scalability_rates, color=colors)
        plt.title('Scalability Comparison (User Achievement Rate)', fontsize=16, fontweight='bold')
        plt.ylabel('User Achievement Rate (%)', fontsize=12)
        plt.xlabel('Database', fontsize=12)
        plt.ylim(0, 110)
        
        # Add value labels on bars and target line
        for bar, value, metrics in zip(bars, scalability_rates, all_metrics):
            plt.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 2, 
                    f'{value:.1f}%', ha='center', va='bottom', fontweight='bold')
            plt.text(bar.get_x() + bar.get_width()/2, bar.get_height()/2, 
                    f'{metrics["max_users_reached"]:,}\\n/{metrics["target_users"]:,}', 
                    ha='center', va='center', fontsize=10, color='white', fontweight='bold')
        
        plt.axhline(y=100, color='red', linestyle='--', alpha=0.7, label='Target (100%)')
        plt.legend()
        plt.tight_layout()
        
        scalability_file = self.results_dir / "scalability_comparison.png"
        plt.savefig(scalability_file, dpi=300, bbox_inches='tight')
        plt.close()
        chart_files['scalability'] = scalability_file
        
        # 4. Performance Score Radar Chart
        if len(all_metrics) > 1:
            fig, ax = plt.subplots(figsize=(10, 8), subplot_kw=dict(projection='polar'))
            
            categories = ['Scalability', 'Throughput', 'Latency', 'Reliability', 'Consistency']
            angles = np.linspace(0, 2 * np.pi, len(categories), endpoint=False).tolist()
            angles += angles[:1]  # Complete the circle
            
            colors = sns.color_palette("husl", len(all_metrics))
            
            for i, metrics in enumerate(all_metrics):
                values = [
                    metrics['scalability_score'],
                    metrics['throughput_score'],
                    metrics['latency_score'],
                    metrics['reliability_score'],
                    metrics['consistency_score']
                ]
                values += values[:1]  # Complete the circle
                
                ax.plot(angles, values, 'o-', linewidth=2, label=metrics['database'], color=colors[i])
                ax.fill(angles, values, alpha=0.25, color=colors[i])
            
            ax.set_xticks(angles[:-1])
            ax.set_xticklabels(categories)
            ax.set_ylim(0, 100)
            ax.set_title('Performance Score Comparison', fontsize=16, fontweight='bold', pad=20)
            ax.legend(loc='upper right', bbox_to_anchor=(1.3, 1.0))
            
            plt.tight_layout()
            radar_file = self.results_dir / "performance_radar.png"
            plt.savefig(radar_file, dpi=300, bbox_inches='tight')
            plt.close()
            chart_files['radar'] = radar_file
        
        return chart_files
    
    def generate_html_report(self, all_metrics: List[Dict], chart_files: Dict[str, str]) -> str:
        """
        Generate comprehensive HTML report
        
        Args:
            all_metrics: List of metrics for all databases
            chart_files: Dictionary of chart file paths
            
        Returns:
            Path to generated HTML report
        """
        # Sort databases by overall score
        sorted_metrics = sorted(all_metrics, key=lambda x: x['overall_score'], reverse=True)
        winner = sorted_metrics[0] if sorted_metrics else None
        
        html_content = f"""
        <!DOCTYPE html>
        <html lang="en">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>Database Performance Comparison Report</title>
            <style>
                body {{
                    font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                    margin: 0;
                    padding: 20px;
                    background-color: #f5f5f5;
                }}
                .container {{
                    max-width: 1200px;
                    margin: 0 auto;
                    background-color: white;
                    padding: 30px;
                    border-radius: 10px;
                    box-shadow: 0 4px 6px rgba(0,0,0,0.1);
                }}
                .header {{
                    text-align: center;
                    margin-bottom: 30px;
                    padding-bottom: 20px;
                    border-bottom: 3px solid #4CAF50;
                }}
                .winner {{
                    background: linear-gradient(135deg, #4CAF50, #45a049);
                    color: white;
                    padding: 20px;
                    border-radius: 10px;
                    margin: 20px 0;
                    text-align: center;
                }}
                .metrics-table {{
                    width: 100%;
                    border-collapse: collapse;
                    margin: 20px 0;
                }}
                .metrics-table th, .metrics-table td {{
                    border: 1px solid #ddd;
                    padding: 12px;
                    text-align: left;
                }}
                .metrics-table th {{
                    background-color: #4CAF50;
                    color: white;
                }}
                .metrics-table tr:nth-child(even) {{
                    background-color: #f2f2f2;
                }}
                .chart-container {{
                    text-align: center;
                    margin: 30px 0;
                }}
                .chart-container img {{
                    max-width: 100%;
                    height: auto;
                    border: 1px solid #ddd;
                    border-radius: 5px;
                }}
                .section {{
                    margin: 30px 0;
                }}
                .section h2 {{
                    color: #4CAF50;
                    border-bottom: 2px solid #4CAF50;
                    padding-bottom: 10px;
                }}
                .score-bar {{
                    width: 100%;
                    height: 20px;
                    background-color: #e0e0e0;
                    border-radius: 10px;
                    overflow: hidden;
                    margin: 5px 0;
                }}
                .score-fill {{
                    height: 100%;
                    background: linear-gradient(90deg, #ff4444, #ffaa00, #4CAF50);
                    border-radius: 10px;
                    transition: width 0.3s ease;
                }}
                .comparison-grid {{
                    display: grid;
                    grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
                    gap: 20px;
                    margin: 20px 0;
                }}
                .db-card {{
                    background-color: #f9f9f9;
                    padding: 20px;
                    border-radius: 8px;
                    border-left: 4px solid #4CAF50;
                }}
                .highlight {{
                    background-color: #e8f5e8;
                    font-weight: bold;
                }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>Database Performance Comparison Report</h1>
                    <p>Generated on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
                    <p>Test Directory: <strong>{self.results_dir.name}</strong></p>
                </div>
        """
        
        # Winner section
        if winner:
            html_content += f"""
                <div class="winner">
                    <h2>🏆 Performance Winner: {winner['database'].upper()}</h2>
                    <p>Overall Score: <strong>{winner['overall_score']:.1f}/100</strong></p>
                    <p>Scalability: {winner['user_achievement_rate']:.1f}% users reached | 
                       Throughput: {winner['requests_per_sec']:.1f} req/s | 
                       Avg Latency: {winner['avg_response_time']:.2f}ms | 
                       Failure Rate: {winner['failure_rate']:.2f}%</p>
                </div>
            """
        
        # Performance Summary Cards
        html_content += """
            <div class="section">
                <h2>Performance Summary</h2>
                <div class="comparison-grid">
        """
        
        for metrics in sorted_metrics:
            highlight_class = "highlight" if metrics == winner else ""
            html_content += f"""
                <div class="db-card {highlight_class}">
                    <h3>{metrics['database'].upper()}</h3>
                    <p><strong>Overall Score:</strong> {metrics['overall_score']:.1f}/100</p>
                    <div class="score-bar">
                        <div class="score-fill" style="width: {metrics['overall_score']}%"></div>
                    </div>
                    <ul>
                        <li><strong>Scalability:</strong> {metrics['user_achievement_rate']:.1f}% ({metrics['max_users_reached']:,} of {metrics['target_users']:,} users)</li>
                        <li><strong>Throughput:</strong> {metrics['requests_per_sec']:.1f} req/s</li>
                        <li><strong>Avg Latency:</strong> {metrics['avg_response_time']:.2f}ms</li>
                        <li><strong>95th Percentile:</strong> {metrics['p95']:.0f}ms</li>
                        <li><strong>Failure Rate:</strong> {metrics['failure_rate']:.2f}%</li>
                    </ul>
                </div>
            """
        
        html_content += """
                </div>
            </div>
        """
        
        # Detailed Metrics Table
        html_content += """
            <div class="section">
                <h2>Detailed Performance Metrics</h2>
                <table class="metrics-table">
                    <tr>
                        <th>Database</th>
                        <th>Scalability</th>
                        <th>Users Reached</th>
                        <th>Requests/sec</th>
                        <th>Avg Latency (ms)</th>
                        <th>95th %ile</th>
                        <th>Failure Rate</th>
                        <th>Overall Score</th>
                    </tr>
        """
        
        for metrics in sorted_metrics:
            highlight_class = "highlight" if metrics == winner else ""
            html_content += f"""
                <tr class="{highlight_class}">
                    <td><strong>{metrics['database'].upper()}</strong></td>
                    <td>{metrics['user_achievement_rate']:.1f}%</td>
                    <td>{metrics['max_users_reached']:,} / {metrics['target_users']:,}</td>
                    <td>{metrics['requests_per_sec']:.1f}</td>
                    <td>{metrics['avg_response_time']:.2f}</td>
                    <td>{metrics['p95']:.0f}</td>
                    <td>{metrics['failure_rate']:.2f}%</td>
                    <td><strong>{metrics['overall_score']:.1f}/100</strong></td>
                </tr>
            """
        
        html_content += """
                </table>
            </div>
        """
        
        # Scalability Analysis
        scalability_leader = max(sorted_metrics, key=lambda x: x['user_achievement_rate'])
        throughput_leader = max(sorted_metrics, key=lambda x: x['requests_per_sec'])
        total_requests_leader = max(sorted_metrics, key=lambda x: x['total_requests'])
        
        html_content += f"""
            <div class="section">
                <h2>🎯 Scalability Analysis - The Real Story</h2>
                <div style="background-color: #f0f8ff; padding: 20px; border-radius: 10px; margin: 20px 0; border-left: 4px solid #4CAF50;">
                    <h3>📊 Objective Reality Check:</h3>
                                         <ul style="font-size: 16px; line-height: 1.6;">
                         <li><strong>Most Users Handled:</strong> {scalability_leader['database'].upper()} reached {scalability_leader['max_users_reached']:,} users ({scalability_leader['user_achievement_rate']:.1f}% of target)</li>
                         <li><strong>Highest Throughput:</strong> {throughput_leader['database'].upper()} achieved {throughput_leader['requests_per_sec']:.1f} req/s</li>
                         <li><strong>Most Total Work:</strong> {total_requests_leader['database'].upper()} processed {total_requests_leader['total_requests']:,} total requests</li>
                         <li><strong>Best Efficiency:</strong> {max(sorted_metrics, key=lambda x: x.get('throughput_per_user', 0))['database'].upper()} with {max(sorted_metrics, key=lambda x: x.get('throughput_per_user', 0)).get('throughput_per_user', 0):.2f} req/s per user</li>
                     </ul>
        """
        
        # Add contextual analysis
        if scalability_leader['database'] != winner['database']:
            html_content += f"""
                    <div style="background-color: #fff3cd; padding: 15px; border-radius: 8px; margin: 15px 0; border-left: 4px solid #ffc107;">
                        <h4>⚠️ Important Context:</h4>
                        <p><strong>{winner['database'].upper()}</strong> won the overall score ({winner['overall_score']:.1f}/100) but only handled <strong>{winner['max_users_reached']:,} users ({winner['user_achievement_rate']:.1f}%)</strong> of the target load.</p>
                        <p><strong>{scalability_leader['database'].upper()}</strong> actually scaled better, handling <strong>{scalability_leader['max_users_reached']:,} users ({scalability_leader['user_achievement_rate']:.1f}%)</strong> - that's <strong>{((scalability_leader['max_users_reached'] / winner['max_users_reached']) - 1) * 100:.0f}% more users!</strong></p>
                        <p>🏆 <em>This suggests {scalability_leader['database'].upper()} has better real-world scalability, while {winner['database'].upper()} performed well under limited load.</em></p>
                    </div>
            """
        
        html_content += """
                </div>
            </div>
        """
        
        # Performance Analysis
        if len(sorted_metrics) > 1:
            second_best = sorted_metrics[1]
            improvement = ((winner['overall_score'] - second_best['overall_score']) / second_best['overall_score']) * 100
            
            html_content += f"""
                <div class="section">
                    <h2>Performance Breakdown</h2>
                    <div class="comparison-grid">
                        <div class="db-card">
                            <h3>Scalability Leader</h3>
                            <p><strong>{scalability_leader['database'].upper()}</strong></p>
                            <p>{scalability_leader['user_achievement_rate']:.1f}% users reached</p>
                            <p>({scalability_leader['max_users_reached']:,} of {scalability_leader['target_users']:,})</p>
                        </div>
                        <div class="db-card">
                            <h3>Throughput Leader</h3>
                            <p><strong>{throughput_leader['database'].upper()}</strong></p>
                            <p>{throughput_leader['requests_per_sec']:.1f} requests/second</p>
                        </div>
                        <div class="db-card">
                            <h3>Latency Leader</h3>
                            <p><strong>{min(sorted_metrics, key=lambda x: x['avg_response_time'])['database'].upper()}</strong></p>
                            <p>{min(sorted_metrics, key=lambda x: x['avg_response_time'])['avg_response_time']:.2f}ms average</p>
                        </div>
                        <div class="db-card">
                            <h3>Score Gap</h3>
                            <p><strong>{improvement:.1f}%</strong></p>
                            <p>{winner['database'].upper()} leads by {improvement:.1f}% in weighted score</p>
                        </div>
                    </div>
                </div>
            """
        
        # Charts Section
        html_content += """
            <div class="section">
                <h2>Performance Charts</h2>
        """
        
        if 'throughput' in chart_files:
            html_content += f"""
                <div class="chart-container">
                    <h3>Throughput Comparison</h3>
                    <img src="{chart_files['throughput'].name}" alt="Throughput Comparison">
                </div>
            """
        
        if 'latency' in chart_files:
            html_content += f"""
                <div class="chart-container">
                    <h3>Latency Percentiles</h3>
                    <img src="{chart_files['latency'].name}" alt="Latency Percentiles">
                </div>
            """
        
        if 'scalability' in chart_files:
            html_content += f"""
                <div class="chart-container">
                    <h3>Scalability Comparison</h3>
                    <img src="{chart_files['scalability'].name}" alt="Scalability Comparison">
                </div>
            """
        
        if 'radar' in chart_files:
            html_content += f"""
                <div class="chart-container">
                    <h3>Overall Performance Radar</h3>
                    <img src="{chart_files['radar'].name}" alt="Performance Radar">
                </div>
            """
        
        # Methodology section
        html_content += f"""
            </div>
            
            <div class="section">
                <h2>📋 Recommendations</h2>
                <div style="background-color: #f8f9fa; padding: 20px; border-radius: 10px; margin: 20px 0;">
        """
        
        # Generate recommendations based on results
        if scalability_leader['database'] != winner['database']:
            html_content += f"""
                    <h3>🎯 For High-Scale Production:</h3>
                    <p><strong>Consider {scalability_leader['database'].upper()}</strong> - It demonstrated superior scalability by handling {scalability_leader['user_achievement_rate']:.1f}% of target users vs {winner['user_achievement_rate']:.1f}% for {winner['database'].upper()}.</p>
                    
                    <h3>🏎️ For Low-Latency Applications:</h3>
                    <p><strong>Consider {winner['database'].upper()}</strong> - It showed excellent performance under moderate load with {winner['avg_response_time']:.2f}ms average latency.</p>
                    
                    <h3>⚙️ Configuration Tuning:</h3>
                    <ul>
                        <li><strong>{scalability_leader['database'].upper()}:</strong> Consider increasing memory/CPU resources to reduce error rate ({scalability_leader['failure_rate']:.2f}%)</li>
                        <li><strong>{winner['database'].upper()}:</strong> Investigate why it stopped scaling at {winner['max_users_reached']:,} users - may need connection pool or configuration tuning</li>
                    </ul>
            """
        else:
            html_content += f"""
                    <h3>🏆 Clear Winner:</h3>
                    <p><strong>{winner['database'].upper()}</strong> dominated in both scoring and scalability - excellent choice for this workload.</p>
                    
                    <h3>📈 Next Steps:</h3>
                    <ul>
                        <li>Test with even higher user loads to find the scaling limits</li>
                        <li>Optimize configuration for production deployment</li>
                        <li>Consider horizontal scaling options</li>
                    </ul>
            """
        
        html_content += """
                </div>
            </div>
            
            <div class="section">
                <h2>Methodology</h2>
                <p>This comparison uses a weighted scoring system to evaluate database performance:</p>
                <ul>
                    <li><strong>Scalability ({self.weights['scalability']*100:.0f}%):</strong> User achievement rate - Higher is better (Critical for real-world performance)</li>
                    <li><strong>Throughput ({self.weights['throughput']*100:.0f}%):</strong> Requests per second - Higher is better</li>
                    <li><strong>Latency ({self.weights['latency']*100:.0f}%):</strong> Average response time - Lower is better</li>
                    <li><strong>Reliability ({self.weights['reliability']*100:.0f}%):</strong> Failure rate - Lower is better</li>
                    <li><strong>Consistency ({self.weights['consistency']*100:.0f}%):</strong> Performance variability - Lower is better</li>
                </ul>
                <p>Each metric is normalized to a 0-100 scale and combined using the weighted formula to produce an overall score.</p>
                <p><strong>Note:</strong> The score winner may not always be the scalability leader. Consider both metrics for real-world decisions.</p>
            </div>
        """
        
        html_content += """
            </div>
        </body>
        </html>
        """
        
        # Write HTML file
        with open(self.report_path, 'w', encoding='utf-8') as f:
            f.write(html_content)
        
        return str(self.report_path)
    
    def run_comparison(self) -> str:
        """
        Run the complete comparison analysis
        
        Returns:
            Path to generated HTML report
        """
        print(f"🔍 Discovering databases in {self.results_dir}...")
        databases = self.discover_databases()
        
        if not databases:
            print("❌ No database test results found!")
            return None
        
        print(f"📊 Found databases: {', '.join(databases)}")
        
        # Load and analyze each database
        all_metrics = []
        for db_name in databases:
            print(f"📈 Analyzing {db_name}...")
            data = self.load_database_data(db_name)
            metrics = self.calculate_performance_metrics(db_name, data)
            all_metrics.append(metrics)
        
        # Calculate performance scores
        print("🧮 Calculating performance scores...")
        all_metrics = self.calculate_performance_scores(all_metrics)
        
        # Generate charts
        print("📊 Generating comparison charts...")
        chart_files = self.generate_comparison_charts(all_metrics)
        
        # Generate HTML report
        print("📄 Generating HTML report...")
        report_path = self.generate_html_report(all_metrics, chart_files)
        
        # Print summary
        sorted_metrics = sorted(all_metrics, key=lambda x: x['overall_score'], reverse=True)
        scalability_leader = max(all_metrics, key=lambda x: x['user_achievement_rate'])
        throughput_leader = max(all_metrics, key=lambda x: x['requests_per_sec'])
        total_requests_leader = max(all_metrics, key=lambda x: x['total_requests'])
        
        print("\n🏆 PERFORMANCE COMPARISON RESULTS:")
        print("=" * 60)
        for i, metrics in enumerate(sorted_metrics, 1):
            print(f"{i}. {metrics['database'].upper()}: {metrics['overall_score']:.1f}/100")
            print(f"   Scalability: {metrics['user_achievement_rate']:.1f}% ({metrics['max_users_reached']:,} of {metrics['target_users']:,} users)")
            print(f"   Throughput: {metrics['requests_per_sec']:.1f} req/s")
            print(f"   Avg Latency: {metrics['avg_response_time']:.2f}ms")
            print(f"   Failure Rate: {metrics['failure_rate']:.2f}%")
            print()
        
        winner = sorted_metrics[0]
        print(f"🥇 SCORE WINNER: {winner['database'].upper()} with {winner['overall_score']:.1f}/100")
        
        # Add scalability analysis to console output
        print("\n🎯 SCALABILITY ANALYSIS:")
        print("=" * 60)
        efficiency_leader = max(all_metrics, key=lambda x: x.get('throughput_per_user', 0))
        print(f"👥 Most Users Handled: {scalability_leader['database'].upper()} ({scalability_leader['max_users_reached']:,} users - {scalability_leader['user_achievement_rate']:.1f}%)")
        print(f"⚡ Highest Throughput: {throughput_leader['database'].upper()} ({throughput_leader['requests_per_sec']:.1f} req/s)")
        print(f"📈 Most Total Work: {total_requests_leader['database'].upper()} ({total_requests_leader['total_requests']:,} requests)")
        print(f"🎯 Best Efficiency: {efficiency_leader['database'].upper()} ({efficiency_leader.get('throughput_per_user', 0):.2f} req/s per user)")
        
        if scalability_leader['database'] != winner['database']:
            scaling_improvement = ((scalability_leader['max_users_reached'] / winner['max_users_reached']) - 1) * 100
            print(f"\n⚠️  IMPORTANT CONTEXT:")
            print(f"   {winner['database'].upper()} won by SCORE but only handled {winner['user_achievement_rate']:.1f}% of target users")
            print(f"   {scalability_leader['database'].upper()} handled {scaling_improvement:.0f}% MORE USERS in practice!")
            print(f"   🏆 {scalability_leader['database'].upper()} shows better REAL-WORLD SCALABILITY")
        else:
            print(f"\n✅ {winner['database'].upper()} dominated both in score AND scalability!")
        
        print(f"\n📊 Report generated: {report_path}")
        
        return report_path


def main():
    """Main function"""
    parser = argparse.ArgumentParser(description='Generate database performance comparison report')
    parser.add_argument('results_dir', help='Directory containing test results (e.g., 100_1m)')
    parser.add_argument('--weights', help='Custom weights as JSON string (e.g., \'{"throughput":0.5,"latency":0.3,"reliability":0.2}\')')
    
    args = parser.parse_args()
    
    # Check if results directory exists
    if not os.path.exists(args.results_dir):
        print(f"❌ Error: Directory '{args.results_dir}' not found!")
        sys.exit(1)
    
    # Create comparator
    comparator = DatabaseComparator(args.results_dir)
    
    # Apply custom weights if provided
    if args.weights:
        try:
            custom_weights = json.loads(args.weights)
            comparator.weights.update(custom_weights)
            print(f"✅ Using custom weights: {comparator.weights}")
        except json.JSONDecodeError:
            print("⚠️  Invalid weights JSON format, using defaults")
    
    # Run comparison
    try:
        report_path = comparator.run_comparison()
        if report_path:
            print(f"\n✅ Comparison complete! Open {report_path} in your browser to view the report.")
        else:
            print("❌ Failed to generate report.")
    except Exception as e:
        print(f"❌ Error during comparison: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main() 