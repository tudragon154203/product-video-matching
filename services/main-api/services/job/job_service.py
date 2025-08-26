from common_py.database import DatabaseManager
from common_py.messaging import MessageBroker
from services.job.job_management_service import JobManagementService
from services.phase.phase_event_service import PhaseEventService
from handlers.database_handler import DatabaseHandler
from handlers.broker_handler import BrokerHandler

class JobService:
    def __init__(self, db: DatabaseManager, broker: MessageBroker):
        self.db = db
        self.broker = broker
        self.db_handler = DatabaseHandler(db)
        self.broker_handler = BrokerHandler(broker)
        self.job_management_service = JobManagementService(self.db_handler, self.broker_handler)
        self.phase_event_service = PhaseEventService(self.db_handler, self.broker_handler)

    async def start_job(self, request):
        """Start a new job"""
        return await self.job_management_service.start_job(request)

    async def get_job(self, job_id: str):
        """Get a complete job record by ID"""
        return await self.job_management_service.get_job(job_id)

    async def get_job_status(self, job_id: str):
        """Get the status of a job"""
        return await self.job_management_service.get_job_status(job_id)

    async def handle_phase_event(self, event_type: str, event_data: dict):
        """Handle a phase event"""
        return await self.phase_event_service.handle_phase_event(event_type, event_data)

    async def list_jobs(self, limit: int = 50, offset: int = 0, status: str = None):
        """List jobs with pagination and optional status filtering"""
        return await self.job_management_service.list_jobs(limit, offset, status)