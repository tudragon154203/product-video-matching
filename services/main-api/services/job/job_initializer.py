import json
import time
from typing import Dict, Any
from fastapi import HTTPException
from common_py.logging_config import configure_logging
from config_loader import config
from models.schemas import StartJobRequest
from services.llm.llm_service import LLMService
from services.llm.prompt_service import PromptService
from handlers.database_handler import DatabaseHandler
from handlers.broker_handler import BrokerHandler

logger = configure_logging("main-api:job_initializer")


class JobInitializer:
    def __init__(self, db_handler: DatabaseHandler, broker_handler: BrokerHandler, llm_service: LLMService, prompt_service: PromptService):
        self.db_handler = db_handler
        self.broker_handler = broker_handler
        self.llm_service = llm_service
        self.prompt_service = prompt_service

    async def initialize_job(self, job_id: str, request: StartJobRequest) -> str:
        query = request.query.strip()

        industry = await self._classify_industry(query)
        queries = await self._generate_queries(query, industry)

        try:
            await self.db_handler.store_job(job_id, query, industry, json.dumps(queries), "collection")
        except Exception as e:
            logger.warning(f"Failed to store job in database: {e}")

        await self._publish_initial_events(job_id, request, queries, industry, query)

        logger.info(
            f"Initialized job (job_id: {job_id}, industry: {industry})")
        return industry

    async def _classify_industry(self, query: str) -> str:
        cls_prompt = self.prompt_service.build_cls_prompt(
            query, config.INDUSTRY_LABELS)
        t0 = time.time()
        try:
            cls_response = await self.llm_service.call_llm("classify", cls_prompt)
            industry = cls_response["response"].strip()
            if industry not in config.INDUSTRY_LABELS:
                industry = "other"
            logger.debug(f"industry from LLM: {industry}")
            return industry
        finally:
            logger.debug(f"llm_classify_ms: {(time.time()-t0)*1000}")

    async def _generate_queries(self, query: str, industry: str) -> Dict[str, Any]:
        gen_prompt = self.prompt_service.build_gen_prompt(query, industry)
        t0 = time.time()
        try:
            gen_response = await self.llm_service.call_llm("generate", gen_prompt, options={"temperature": 0.2})
            # logger.info("response from LLM: %s", gen_response)

            # Pass the raw response string to normalize_queries, which will handle JSON parsing
            raw_response = gen_response["response"]
            queries = self.prompt_service.normalize_queries(
                raw_response, min_items=2, max_items=4)
            logger.debug("queries from LLM: %s", queries)

            return queries
        finally:
            logger.debug(f"llm_generate_ms: {(time.time()-t0)*1000}")

    async def _publish_initial_events(self, job_id: str, request: StartJobRequest, queries: Dict[str, Any], industry: str, original_query: str):
        try:
            await self.broker_handler.publish_product_collection_request(
                job_id,
                request.top_amz,
                request.top_ebay,
                {"en": queries["product"]["en"]}
            )

            video_queries = self.prompt_service.route_video_queries(
                queries, request.platforms)
            await self.broker_handler.publish_video_search_request(
                job_id,
                industry,
                video_queries,
                request.platforms,
                request.recency_days
            )
        except Exception as e:
            logger.warning(f"Failed to publish events: {e}")
