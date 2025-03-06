from datetime import datetime
from sqlalchemy import Column, Integer, String, Float, DateTime, MetaData, Table, create_engine, inspect
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import logging

Base = declarative_base()
metadata = MetaData()

logger = logging.getLogger(__name__)

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

class Database:
    def __init__(self, database_url):
        self.engine = create_engine(database_url)
        self.metadata = metadata
        self.session = sessionmaker(bind=self.engine)()
        Base.metadata.create_all(self.engine)
        self.table_cache = {}
        self.inspector = inspect(self.engine)
        logger.info(f"Database initialized with URL: {database_url}")

    def create_metric_table(self, table_name: str, metrics: dict):
        """Dynamically create a metrics table"""
        if table_name in self.table_cache:
            logger.info(f"Using cached table for {table_name}")
            return self.table_cache[table_name]

        logger.info(f"Creating new table {table_name} with metrics: {metrics}")
        columns = {
            'id': Column(Integer, primary_key=True),
            'timestamp': Column(DateTime, default=datetime.utcnow),
        }
        
        # Add columns based on metrics
        for key, value_type in metrics.items():
            if value_type == "TEXT":
                columns[key] = Column(String)
            else:
                columns[key] = Column(Float)
        
        # Create table class dynamically
        metric_table = type(
            f'Metrics{table_name.title().replace("_", "")}',
            (Base,),
            {
                '__tablename__': table_name,
                **{k: v for k, v in columns.items()}
            }
        )

        if not self.inspector.has_table(table_name):
            logger.info(f"Creating table {table_name} in database")
            metric_table.__table__.create(self.engine)
        else:
            logger.info(f"Table {table_name} already exists")

        self.table_cache[table_name] = metric_table
        return metric_table

    def get_metric_table(self, table_name: str):
        """Get existing metric table if it exists"""
        if table_name in self.table_cache:
            return self.table_cache[table_name]
        
        # If not in cache but exists in database, create model
        if self.inspector.has_table(table_name):
            columns = self.inspector.get_columns(table_name)
            metrics = {
                col['name']: col['type']
                for col in columns
                if col['name'] not in ['id', 'timestamp']
            }
            return self.create_metric_table(table_name, metrics)
            
        logger.warning(f"Table {table_name} not found")
        return None

    def get_session(self):
        return self.session 