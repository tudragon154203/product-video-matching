from common_py.database import DatabaseManager
from common_py.messaging import MessageBroker
from services.job_management_service import JobManagementService
from services.phase_management_service import PhaseManagementService
from handlers.database_handler import DatabaseHandler
from handlers.broker_handler import BrokerHandler

class JobService:
    def __init__(self, db: DatabaseManager, broker: MessageBroker):
        self.db = db
        self.broker = broker
        self.db_handler = DatabaseHandler(db)
        self.broker_handler = BrokerHandler(broker)
        self.job_management_service = JobManagementService(self.db_handler, self.broker_handler)
        self.phase_management_service = PhaseManagementService(self.db_handler, self.broker_handler)

    async def start_job(self, request):
        """Start a new job"""
        return await self.job_management_service.start_job(request)

    async def get_job_status(self, job_id: str):
        """Get the status of a job"""
        return await self.job_management_service.get_job_status(job_id)

    async def update_job_phases(self):
        """Update job phases"""
        return await self.phase_management_service.update_job_phases()

    async def phase_update_task(self):
        """Run the phase update task"""
        return await self.phase_management_service.phase_update_task()