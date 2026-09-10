import os
import logging
from typing import Optional, List, Dict, Any
from app.config import settings

def setup_logging():
    """
    Configure application-wide structured logging and ensure Langfuse env vars are propagated.
    """
    level = getattr(logging, settings.log_level.upper(), logging.INFO)
    
    # Configure the root logger
    logging.basicConfig(
        level=level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%dT%H:%M:%S'
    )
    
    # Mute noisy third-party loggers if needed
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("langchain").setLevel(logging.WARNING)
    logging.getLogger("langfuse").setLevel(logging.INFO)

    # Propagate Langfuse credentials to environment for SDK v4 auto-discovery
    if settings.is_langfuse_enabled():
        if settings.langfuse_public_key:
            os.environ["LANGFUSE_PUBLIC_KEY"] = settings.langfuse_public_key
        if settings.langfuse_secret_key:
            os.environ["LANGFUSE_SECRET_KEY"] = settings.langfuse_secret_key
        os.environ["LANGFUSE_HOST"] = settings.effective_langfuse_host
        os.environ["LANGFUSE_BASE_URL"] = settings.effective_langfuse_host

def get_logger(name: str) -> logging.Logger:
    """
    Get a structured logger for the specified module.
    """
    return logging.getLogger(name)

def get_langfuse_callback(
    user_id: Optional[str] = None,
    session_id: Optional[str] = None,
    trace_name: Optional[str] = "it-support-request",
    tags: Optional[List[str]] = None,
    metadata: Optional[Dict[str, Any]] = None,
) -> Optional[object]:
    """
    Returns a configured Langfuse CallbackHandler following Langfuse SDK v4 best practices:
    - Uses langfuse.langchain.CallbackHandler with TraceContext
    - Propagates user_id and session_id for user tracking and conversation grouping
    - Attaches metadata and environment tags for dashboard filtering
    """
    if settings.is_langfuse_enabled():
        try:
            # Ensure env vars are set
            os.environ["LANGFUSE_PUBLIC_KEY"] = settings.langfuse_public_key or ""
            os.environ["LANGFUSE_SECRET_KEY"] = settings.langfuse_secret_key or ""
            os.environ["LANGFUSE_HOST"] = settings.effective_langfuse_host
            os.environ["LANGFUSE_BASE_URL"] = settings.effective_langfuse_host

            from langfuse.langchain import CallbackHandler
            from langfuse.types import TraceContext
            
            default_tags = ["it-support-assistant", settings.app_env]
            if tags:
                default_tags.extend(tags)
                
            default_metadata = {
                "model": settings.groq_model,
                "environment": settings.app_env,
            }
            if metadata:
                default_metadata.update(metadata)
                
            trace_context = TraceContext(
                user_id=user_id,
                session_id=session_id,
                trace_name=trace_name,
                tags=list(set(default_tags)),
                metadata=default_metadata,
            )
            
            return CallbackHandler(
                public_key=settings.langfuse_public_key,
                trace_context=trace_context,
            )
        except ImportError:
            get_logger(__name__).warning("Langfuse enabled in settings, but package not installed.")
            return None
        except Exception as e:
            get_logger(__name__).warning(f"Failed to initialize Langfuse callback: {str(e)}")
            return None
    return None

def flush_langfuse(handler: Optional[object] = None):
    """
    Flushes queued Langfuse traces to ensure no data is lost before request completion.
    """
    if handler and hasattr(handler, "flush"):
        try:
            handler.flush()
        except Exception as e:
            get_logger(__name__).warning(f"Error flushing Langfuse handler: {str(e)}")
    else:
        try:
            from langfuse import get_client
            client = get_client()
            if client and hasattr(client, "flush"):
                client.flush()
        except Exception:
            pass
