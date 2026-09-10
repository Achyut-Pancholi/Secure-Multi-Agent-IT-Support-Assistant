import uuid
import json
import asyncio
from fastapi import APIRouter, Depends, WebSocket, WebSocketDisconnect
from fastapi.responses import StreamingResponse
from app.api.schemas import SupportRequestSchema, SupportResponseSchema
from app.api.auth import verify_app_token
from app.graph.workflow import build_workflow
from app.observability.logging import get_logger, get_langfuse_callback, flush_langfuse
from app.observability.metrics import MetricsTimer

logger = get_logger(__name__)
router = APIRouter()
app_workflow = build_workflow()

@router.post("/support", response_model=SupportResponseSchema)
async def submit_support_request(
    request: SupportRequestSchema, 
    token: str = Depends(verify_app_token)
):
    with MetricsTimer() as timer:
        request_id = str(uuid.uuid4())
        logger.info(f"Received support request {request_id} for user {request.user_id}")
        
        initial_state = {
            "request_id": request_id,
            "user_id": request.user_id,
            "user_query": request.query,
            "history": request.history,
        }
        
        langfuse_cb = get_langfuse_callback(
            user_id=request.user_id,
            session_id=request_id,
            trace_name="support-request",
            metadata={"request_id": request_id, "endpoint": "/api/v1/support"}
        )
        config = {"callbacks": [langfuse_cb]} if langfuse_cb else {}
        
        try:
            final_state = app_workflow.invoke(initial_state, config=config)
        finally:
            flush_langfuse(langfuse_cb)
        
        status = "error" if final_state.get("errors") else "completed"
        if status == "completed":
            timer.success()
            
        return SupportResponseSchema(
            request_id=request_id,
            response=final_state.get("final_response", ""),
            status=status
        )

@router.post("/support/stream")
async def stream_support_request(
    request: SupportRequestSchema,
    token: str = Depends(verify_app_token)
):
    """
    Streaming endpoint using Server-Sent Events (SSE)
    """
    request_id = str(uuid.uuid4())
    logger.info(f"Received streaming support request {request_id} for user {request.user_id}")
    
    initial_state = {
        "request_id": request_id,
        "user_id": request.user_id,
        "user_query": request.query,
        "history": request.history,
    }
    
    langfuse_cb = get_langfuse_callback(
        user_id=request.user_id,
        session_id=request_id,
        trace_name="support-stream",
        metadata={"request_id": request_id, "endpoint": "/api/v1/support/stream"}
    )
    config = {"callbacks": [langfuse_cb]} if langfuse_cb else {}

    async def event_generator():
        with MetricsTimer() as timer:
            yield f"data: {json.dumps({'event': 'request_received', 'request_id': request_id})}\n\n"
            try:
                for step_event in app_workflow.stream(initial_state, config=config):
                    node_name = list(step_event.keys())[0]
                    node_data = step_event[node_name]
                    
                    yield f"data: {json.dumps({'event': f'{node_name}_completed'})}\n\n"
                    
                    if node_name == "output_guardrail":
                        final_resp = node_data.get("final_response", "")
                        yield f"data: {json.dumps({'event': 'completed', 'response': final_resp})}\n\n"
                        timer.success()
            except Exception as e:
                logger.error(f"Error in stream: {str(e)}")
                yield f"data: {json.dumps({'event': 'error', 'message': str(e)})}\n\n"
            finally:
                flush_langfuse(langfuse_cb)
            
    return StreamingResponse(event_generator(), media_type="text/event-stream")

@router.websocket("/ws/runs/{request_id}")
async def websocket_endpoint(websocket: WebSocket, request_id: str):
    """
    WebSocket endpoint for bidirectional real-time progress monitoring.
    """
    await websocket.accept()
    logger.info(f"WebSocket connected for request_id: {request_id}")
    langfuse_cb = None
    try:
        data = await websocket.receive_text()
        payload = json.loads(data)
        user_id = payload.get("user_id", "anonymous")
        user_query = payload.get("query", "")
        
        initial_state = {
            "request_id": request_id,
            "user_id": user_id,
            "user_query": user_query,
        }
        
        langfuse_cb = get_langfuse_callback(
            user_id=user_id,
            session_id=request_id,
            trace_name="support-websocket",
            metadata={"request_id": request_id, "endpoint": f"/ws/runs/{request_id}"}
        )
        config = {"callbacks": [langfuse_cb]} if langfuse_cb else {}
        
        await websocket.send_json({"event": "request_received", "request_id": request_id})
        
        with MetricsTimer() as timer:
            def run_stream():
                return list(app_workflow.stream(initial_state, config=config))
                
            steps = await asyncio.to_thread(run_stream)
            
            for step_event in steps:
                node_name = list(step_event.keys())[0]
                node_data = step_event[node_name]
                await websocket.send_json({"event": f"{node_name}_completed"})
                
                if node_name == "output_guardrail":
                    final_resp = node_data.get("final_response", "")
                    await websocket.send_json({"event": "completed", "response": final_resp})
                    timer.success()
                    
    except WebSocketDisconnect:
        logger.info(f"WebSocket disconnected for request_id: {request_id}")
    except Exception as e:
        logger.error(f"WebSocket error: {str(e)}")
        await websocket.send_json({"event": "error", "message": str(e)})
    finally:
        flush_langfuse(langfuse_cb)
        try:
            await websocket.close()
        except:
            pass
