#!/usr/bin/env python3
"""
Tests for data quality checking functionality.

Coverage:
- Nil value detection thresholds
- Timestamp anomaly detection
- Duplicate transaction detection
- Statistical outlier detection
"""

import json
import os
import tempfile
from pathlib import Path

import pandas as pd
import pytest

from scripts.data_quality_check import DataQualityChecker


@pytest.fixture
def sample_dataframe():
    """Create a sample DataFrame for testing."""
    from datetime import datetime, timedelta
    
    # Use recent timestamps to avoid "very_old_timestamp" anomalies
    now = datetime.now()
    dates = [(now - timedelta(days=i)).strftime('%Y-%m-%d') for i in range(5, 0, -1)]
    
    return pd.DataFrame({
        'id': [1, 2, 3, 4, 5],
        'timestamp': dates,
        'value': [10.0, 20.0, 30.0, 40.0, 50.0],
        'category': ['A', 'B', 'C', 'D', 'E']
    })


@pytest.fixture
def dataframe_with_nil():
    """Create a DataFrame with high nil percentages."""
    df = pd.DataFrame({
        'id': [1, 2, 3, 4, 5],
        'good_column': [1.0, 2.0, 3.0, 4.0, 5.0],
        'medium_nil': [1.0, None, 3.0, None, 5.0],  # 40% nil
        'high_nil': [None, None, None, 4.0, None],  # 80% nil
    })
    return df


@pytest.fixture
def dataframe_with_duplicates():
    """Create a DataFrame with duplicates."""
    df = pd.DataFrame({
        'id': [1, 2, 2, 3, 4],  # duplicate ID
        'value': [10, 20, 20, 30, 40],
    })
    return df


@pytest.fixture
def dataframe_with_timestamp_anomalies():
    """Create a DataFrame with timestamp anomalies."""
    df = pd.DataFrame({
        'id': [1, 2, 3, 4],
        'normal_time': ['2024-01-01', '2024-01-02', '2024-01-03', '2024-01-04'],
        'future_time': ['2099-01-01', '2099-01-02', '2099-01-03', '2099-01-04'],
    })
    return df


class TestNilValueDetection:
    """Tests for nil/NaN value detection."""

    def test_no_nil_values(self, sample_dataframe):
        """Test detection when there are no nil values."""
        checker = DataQualityChecker()
        result = checker._check_nil_values(sample_dataframe)
        
        assert result['max_nil_percentage'] == 0.0
        assert len(result['high_nil_columns']) == 0

    def test_high_nil_detection(self, dataframe_with_nil):
        """Test detection of high nil percentage columns."""
        checker = DataQualityChecker()
        result = checker._check_nil_values(dataframe_with_nil)
        
        high_nil_cols = [c['column'] for c in result['high_nil_columns']]
        assert 'high_nil' in high_nil_cols
        
        medium_nil_cols = [c['column'] for c in result['high_nil_columns'] if c['severity'] == 'MEDIUM']
        assert 'medium_nil' in [c['column'] for c in result['high_nil_columns']]

    def test_nil_percentage_calculation(self, dataframe_with_nil):
        """Test accurate nil percentage calculation."""
        checker = DataQualityChecker()
        result = checker._check_nil_values(dataframe_with_nil)
        
        assert result['nil_percentages']['high_nil'] == 80.0
        assert result['nil_percentages']['medium_nil'] == 40.0


class TestTimestampAnomalyDetection:
    """Tests for timestamp anomaly detection."""

    def test_normal_timestamps(self, sample_dataframe):
        """Test with normal timestamps."""
        checker = DataQualityChecker()
        result = checker._check_timestamps(sample_dataframe)
        
        assert len(result['anomalies']) == 0

    def test_future_timestamp_detection(self, dataframe_with_timestamp_anomalies):
        """Test detection of future timestamps."""
        checker = DataQualityChecker()
        result = checker._check_timestamps(dataframe_with_timestamp_anomalies)
        
        future_anomalies = [a for a in result['anomalies'] if a['type'] == 'future_timestamp']
        assert len(future_anomalies) > 0


class TestDuplicateDetection:
    """Tests for duplicate transaction detection."""

    def test_no_duplicates(self, sample_dataframe):
        """Test when there are no duplicates."""
        checker = DataQualityChecker()
        result = checker._check_duplicates(sample_dataframe)
        
        assert result['duplicate_count'] == 0
        assert result['full_duplicate_rows'] == 0

    def test_duplicate_ids(self, dataframe_with_duplicates):
        """Test detection of duplicate IDs."""
        checker = DataQualityChecker()
        result = checker._check_duplicates(dataframe_with_duplicates)
        
        assert result['duplicate_count'] > 0
        assert 'id' in result['id_column_duplicates']


class TestStatisticalAnalysis:
    """Tests for statistical analysis."""

    def test_numeric_column_detection(self, sample_dataframe):
        """Test detection of numeric columns."""
        checker = DataQualityChecker()
        result = checker._check_statistics(sample_dataframe)
        
        # 'id' and 'value' are both numeric
        assert result['numeric_columns'] == 2

    def test_outlier_detection(self):
        """Test outlier detection using IQR method."""
        checker = DataQualityChecker()
        
        # Create series with clear outliers
        series = pd.Series([1, 2, 3, 4, 5, 100])  # 100 is an outlier
        outliers = checker._detect_outliers(series)
        
        assert outliers >= 1


class TestFullFileCheck:
    """Tests for complete file checking workflow."""

    def test_file_check_integration(self, sample_dataframe):
        """Test complete file check workflow."""
        checker = DataQualityChecker()
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as f:
            sample_dataframe.to_csv(f.name, index=False)
            temp_path = Path(f.name)
        
        try:
            result = checker.check_file(temp_path)
            
            assert result['rows'] == 5
            assert result['columns'] == 4
            assert result['status'] == 'PASSED'
        finally:
            os.unlink(temp_path)


class TestReportGeneration:
    """Tests for report generation."""

    def test_report_save(self, sample_dataframe):
        """Test saving quality report to JSON."""
        checker = DataQualityChecker()
        
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = os.path.join(tmpdir, 'test_report.json')
            
            with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as f:
                sample_dataframe.to_csv(f.name, index=False)
                temp_path = Path(f.name)
            
            try:
                checker.check_file(temp_path)
                checker.save_report(output_path)
                
                assert os.path.exists(output_path)
                
                with open(output_path, 'r') as f:
                    report = json.load(f)
                
                assert 'timestamp' in report
                assert 'files_checked' in report
            finally:
                os.unlink(temp_path)


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
