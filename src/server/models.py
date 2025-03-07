from datetime import datetime
from sqlalchemy import Column, Integer, String, Float, DateTime
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()

class UEFARanking(Base):
    __tablename__ = 'uefa_rankings'

    id = Column(Integer, primary_key=True)
    club = Column(String, nullable=False)
    points = Column(Float, nullable=False)
    year = Column(Integer, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow)

class DeviceCommand(Base):
    __tablename__ = 'device_commands'

    id = Column(Integer, primary_key=True)
    device_id = Column(String, nullable=False)
    command = Column(String, nullable=False)
    status = Column(String, default='pending')
    created_at = Column(DateTime, default=datetime.utcnow)
    executed_at = Column(DateTime, nullable=True)
    response = Column(String, nullable=True)

# Base class for dynamic metric tables
class MetricBase:
    id = Column(Integer, primary_key=True)
    timestamp = Column(DateTime, default=datetime.utcnow)
    
    @classmethod
    def create_table(cls, table_name, columns):
        """Create a new metric table class"""
        table_dict = {
            '__tablename__': table_name,
            'id': cls.id,
            'timestamp': cls.timestamp
        }
        
        # Add dynamic columns
        for name, type_ in columns.items():
            if type_ == "FLOAT":
                table_dict[name] = Column(Float)
            else:
                table_dict[name] = Column(String)
                
        return type(f'Metrics{table_name.title().replace("_", "")}', (Base,), table_dict) 