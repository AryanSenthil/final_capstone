"""
Database Management Module

Main entry point for sensor data ingestion and processing.
"""

from .ingest_sensor_data import ingest_sensor_data

__all__ = ['ingest_sensor_data']