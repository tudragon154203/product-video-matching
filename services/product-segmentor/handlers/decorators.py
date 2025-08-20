import functools
from contracts.validator import validator
from common_py.logging_config import configure_logging

logger = configure_logging("product-segmentor")

def validate_event(schema_name):
    """Decorator to validate event data against a schema"""
    def decorator(func):
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            try:
                # Extract event_data from args (position 1) or kwargs
                event_data = args[1] if len(args) > 1 else kwargs.get('event_data')
                if not event_data:
                    raise ValueError("Event data not found in arguments")
                
                # Log the event data structure before validation
                logger.info(f"Validating event for {schema_name}",
                           schema_name=schema_name,
                           event_keys=list(event_data.keys()) if isinstance(event_data, dict) else "not_dict",
                           event_type=type(event_data).__name__)
                
                # Log specific required fields for videos_keyframes_ready
                if schema_name == "videos_keyframes_ready" and isinstance(event_data, dict):
                    logger.info("Videos keyframes ready validation details",
                               video_id=event_data.get("video_id"),
                               job_id=event_data.get("job_id"),
                               frames_count=len(event_data.get("frames", [])),
                               frames_keys=list(event_data.get("frames", [{}])[0].keys()) if event_data.get("frames") and len(event_data.get("frames", [])) > 0 else "no_frames")
                
                validator.validate_event(schema_name, event_data)
                return await func(*args, **kwargs)
            except Exception as e:
                logger.error(f"Validation failed for {schema_name}: {str(e)}")
                # Debug: Log the full event data structure for debugging
                logger.error("Failed event data structure",
                           schema_name=schema_name,
                           event_data=event_data,
                           event_type=type(event_data).__name__)
                raise
        return wrapper
    return decorator

def handle_errors(func):
    """Decorator to handle and log errors in event handlers"""
    @functools.wraps(func)
    async def wrapper(*args, **kwargs):
        try:
            return await func(*args, **kwargs)
        except Exception as e:
            logger.error(f"Error in {func.__name__}: {str(e)}")
            raise
    return wrapper