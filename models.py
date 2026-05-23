from dataclasses import dataclass
from datetime import datetime
from typing import Dict, Any, List

@dataclass
class MonitoringEvent:
    client_id: str
    data_type: str  # 'hardware', 'usb', 'print', 'process', 'website'
    timestamp: datetime
    payload: Dict[str, Any]

@dataclass
class HardwareSnapshot:
    client_id: str
    snapshot_date: datetime
    hardware_data: Dict[str, Any]
    software_data: Dict[str, Any]

@dataclass
class ClientInfo:
    client_id: str
    computer_name: str
    ip_address: str
    last_seen: datetime
    created_at: datetime

@dataclass
class ReportRequest:
    client_id: str
    hours: int
    target_date: datetime
    data_type: str = None