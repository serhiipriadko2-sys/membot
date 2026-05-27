#!/usr/bin/env python3
"""
Data Quality Check Script for Membot Project

Performs comprehensive data quality validation on processed CSV files:
- Nil/NaN percentage analysis
- Timestamp anomaly detection
- Duplicate transaction detection
- Schema validation
- Statistical outlier detection

Usage:
    python scripts/data_quality_check.py [--output reports/data_quality_report.json]
"""

import argparse
import json
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

import pandas as pd


class DataQualityChecker:
    """Comprehensive data quality validation for membot datasets."""

    def __init__(self, data_dir: str = "data/processed"):
        self.data_dir = Path(data_dir)
        self.results: Dict[str, Any] = {
            "timestamp": datetime.now().isoformat(),
            "files_checked": 0,
            "total_issues": 0,
            "files": {}
        }

    def check_file(self, filepath: Path) -> Dict[str, Any]:
        """Perform all quality checks on a single file."""
        print(f"Checking {filepath.name}...")

        try:
            df = pd.read_csv(filepath)
        except Exception as e:
            return {
                "error": str(e),
                "status": "FAILED"
            }

        results = {
            "rows": len(df),
            "columns": len(df.columns),
            "column_names": list(df.columns),
            "nil_analysis": self._check_nil_values(df),
            "timestamp_analysis": self._check_timestamps(df),
            "duplicate_analysis": self._check_duplicates(df),
            "statistical_analysis": self._check_statistics(df),
            "status": "PASSED"
        }

        # Determine overall status
        issues = []
        if results["nil_analysis"]["high_nil_columns"]:
            issues.extend(results["nil_analysis"]["high_nil_columns"])
        if results["timestamp_analysis"]["anomalies"]:
            issues.append("timestamp_anomalies")
        if results["duplicate_analysis"]["duplicate_count"] > 0:
            issues.append("duplicates_found")

        if issues:
            results["status"] = "WARNING"
            results["issues"] = issues
            self.results["total_issues"] += len(issues)

        return results

    def _check_nil_values(self, df: pd.DataFrame) -> Dict[str, Any]:
        """Check percentage of nil/NaN values per column."""
        nil_percentages = (df.isna().sum() / len(df) * 100).round(2)

        high_nil = []
        for col, pct in nil_percentages.items():
            if pct > 50:
                high_nil.append({"column": col, "percentage": pct, "severity": "HIGH"})
            elif pct > 20:
                high_nil.append({"column": col, "percentage": pct, "severity": "MEDIUM"})
            elif pct > 5:
                high_nil.append({"column": col, "percentage": pct, "severity": "LOW"})

        return {
            "nil_percentages": nil_percentages.to_dict(),
            "high_nil_columns": high_nil,
            "max_nil_percentage": float(nil_percentages.max()) if len(nil_percentages) > 0 else 0
        }

    def _check_timestamps(self, df: pd.DataFrame) -> Dict[str, Any]:
        """Detect timestamp anomalies."""
        anomalies = []
        timestamp_cols = [col for col in df.columns if 'time' in col.lower() or 'date' in col.lower() or 'ts' in col.lower()]

        for col in timestamp_cols:
            if col not in df.columns:
                continue

            try:
                # Try to parse as datetime
                if df[col].dtype == 'object':
                    ts_series = pd.to_datetime(df[col], errors='coerce')
                else:
                    ts_series = pd.to_datetime(df[col], errors='coerce', unit='s')

                # Check for future timestamps
                future_mask = ts_series > datetime.now()
                if future_mask.any():
                    anomalies.append({
                        "column": col,
                        "type": "future_timestamp",
                        "count": int(future_mask.sum())
                    })

                # Check for very old timestamps (> 1 year)
                old_mask = ts_series < (datetime.now() - pd.Timedelta(days=365))
                if old_mask.any():
                    anomalies.append({
                        "column": col,
                        "type": "very_old_timestamp",
                        "count": int(old_mask.sum())
                    })

                # Check for duplicates in timestamps
                if ts_series.duplicated().any():
                    anomalies.append({
                        "column": col,
                        "type": "duplicate_timestamps",
                        "count": int(ts_series.duplicated().sum())
                    })

            except Exception:
                pass  # Column is not a timestamp

        return {
            "timestamp_columns": timestamp_cols,
            "anomalies": anomalies
        }

    def _check_duplicates(self, df: pd.DataFrame) -> Dict[str, Any]:
        """Detect duplicate transactions."""
        # Check for completely duplicate rows
        full_duplicates = df.duplicated().sum()

        # Check for duplicate IDs/transactions if applicable
        id_cols = [col for col in df.columns if 'id' in col.lower() or 'hash' in col.lower() or 'signature' in col.lower()]
        id_duplicates = {}

        for col in id_cols:
            if col in df.columns:
                dup_count = df[col].duplicated().sum()
                if dup_count > 0:
                    id_duplicates[col] = int(dup_count)

        return {
            "full_duplicate_rows": int(full_duplicates),
            "id_column_duplicates": id_duplicates,
            "duplicate_count": int(full_duplicates) + sum(id_duplicates.values())
        }

    def _check_statistics(self, df: pd.DataFrame) -> Dict[str, Any]:
        """Basic statistical analysis for numeric columns."""
        numeric_cols = df.select_dtypes(include=['number']).columns
        stats = {}

        for col in numeric_cols:
            series = df[col].dropna()
            if len(series) == 0:
                continue

            stats[col] = {
                "mean": float(series.mean()),
                "std": float(series.std()),
                "min": float(series.min()),
                "max": float(series.max()),
                "median": float(series.median()),
                "outliers_detected": self._detect_outliers(series)
            }

        return {
            "numeric_columns": len(numeric_cols),
            "statistics": stats
        }

    def _detect_outliers(self, series: pd.Series) -> int:
        """Detect outliers using IQR method."""
        Q1 = series.quantile(0.25)
        Q3 = series.quantile(0.75)
        IQR = Q3 - Q1

        lower_bound = Q1 - 1.5 * IQR
        upper_bound = Q3 + 1.5 * IQR

        outliers = ((series < lower_bound) | (series > upper_bound)).sum()
        return int(outliers)

    def run_all_checks(self) -> Dict[str, Any]:
        """Run quality checks on all processed CSV files."""
        csv_files = list(self.data_dir.glob("*.csv"))

        if not csv_files:
            print(f"No CSV files found in {self.data_dir}")
            return self.results

        for filepath in csv_files:
            file_results = self.check_file(filepath)
            self.results["files"][filepath.name] = file_results
            self.results["files_checked"] += 1

        return self.results

    def save_report(self, output_path: str) -> None:
        """Save quality report to JSON file."""
        with open(output_path, 'w') as f:
            json.dump(self.results, f, indent=2, default=str)
        print(f"Report saved to {output_path}")


def main():
    parser = argparse.ArgumentParser(description="Data Quality Check for Membot")
    parser.add_argument(
        "--data-dir",
        default="data/processed",
        help="Directory containing processed CSV files"
    )
    parser.add_argument(
        "--output",
        default="reports/data_quality_report.json",
        help="Output path for quality report"
    )

    args = parser.parse_args()

    # Ensure reports directory exists
    os.makedirs("reports", exist_ok=True)

    checker = DataQualityChecker(args.data_dir)
    results = checker.run_all_checks()
    checker.save_report(args.output)

    # Print summary
    print("\n" + "="*60)
    print("DATA QUALITY SUMMARY")
    print("="*60)
    print(f"Files checked: {results['files_checked']}")
    print(f"Total issues: {results['total_issues']}")

    for filename, file_results in results['files'].items():
        status = file_results.get('status', 'UNKNOWN')
        status_icon = "✅" if status == "PASSED" else "⚠️" if status == "WARNING" else "❌"
        print(f"  {status_icon} {filename}: {status}")

    print("="*60)

    # Exit with error code if there are critical issues
    sys.exit(0 if results['total_issues'] == 0 else 1)


if __name__ == "__main__":
    main()
