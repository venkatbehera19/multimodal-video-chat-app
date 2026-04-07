from fastapi import APIRouter, status, Query, HTTPException

from app.config.env_config import settings
from app.config.log_config import logger
from app.prompt.retrival_system_prompt import RAG_SYSTEM_PROMPT_TEXT
# from app.llm.groq_chat_client import default_chat_client
# from app.utils.redis_utils import redis_history
from app.repository.lamma_repo import LammaRepository
from llama_index.core.response_synthesizers import TreeSummarize
from llama_index.core.query_engine import SimpleMultiModalQueryEngine
from app.llm.gemini_multi_modal import gemini_default_chat_client


router = APIRouter(tags=['chat'])
repo = LammaRepository()
index = repo.get_index()

@router.get('/chat', status_code=status.HTTP_200_OK)
async def chat(query: str, session_id: str, video_id: str = Query(..., description="The ID of the video to query")):
# async def chat(query: str, session_id: str, link: str = Query(..., description="The processed video link")):
#     """ Chat Methods for llm response

#     Args:
#         query: user message to llm
#         session_id: session to keep track of the messages
#         link: youtube link that need to summerize

#     Response:
#         answer: llm answer with similarity search
#     """
#     video_id = link.split("v=")[-1]
#     history = redis_history.get_redis_history(session_id)

#     prompt_template = ChatPromptTemplate.from_template(RAG_SYSTEM_PROMPT_TEXT)

#     basic_chain = prompt_template | default_chat_client | StrOutputParser()

#     text_results = text_embedding_vector_store.search(query=query, k=3)
#     image_results = image_embedding_vector_store.search_images(query=query, k=2, video_id=video_id)

#     context_text = "\n".join([doc.page_content for doc in text_results])
#     visual_context = "\n".join([
#         f"Frame at {res.payload.get('timestamp', 'unknown time')} shows: {res.payload.get('description', 'visual match')}" 
#         for res in image_results
#     ])

#     config = {"configurable": { "session_id": session_id }}

#     logger.info(f"context_text {context_text}", )

#     if settings.USE_REDIS:
#         with_message_history_runnable = RunnableWithMessageHistory(
#             basic_chain,
#             get_session_history=redis_history.get_redis_history,
#             input_messages_key="query",
#             history_messages_key="history",
#         )

#     try:
#         response_text = await with_message_history_runnable.ainvoke(
#             {"query": query, "context": context_text, "visual_context": visual_context}, 
#             config=config
#         )
#         source_frames = [
#             {
#             "timestamp": res.payload.get("timestamp"),
#             "image_base64": res.payload.get("base64_image"),
#             "score": getattr(res, "score", None)
#             }
#             for res in image_results
#         ]
#         return {
#             "answer": response_text,
#             "session_id": session_id,
#             "sources": {
#             "frames": source_frames,
#             "text_snippets": [doc.page_content for doc in text_results]
#         }
#         }
#     except Exception as e:
#         error_msg = str(e)
#         logger.error(f"Chain error: {error_msg}")
    try:
        
        if not index:
            raise HTTPException(status_code=404, detail="Video index not found. Process the video first.")
        
        retriever = index.as_retriever(
            similarity_top_k=3, 
            image_similarity_top_k=3
        )

        query_engine = SimpleMultiModalQueryEngine(
            retriever=retriever,
            multi_modal_llm=gemini_default_chat_client
        )

        response = query_engine.query(query)

        return {
        "answer": response.response,
        "session_id": session_id,
        "sources": {
            "frames": [
                node.node.metadata.get("file_path") 
                for node in response.source_nodes 
                if hasattr(node.node, 'image')
            ],
            "text_snippets": [
                node.node.text 
                for node in response.source_nodes 
                if not hasattr(node.node, 'image')
            ]
        }
    }

    except Exception as e:
        logger.error(f"Chat Error: {str(e)}")
        raise HTTPException(status_code=500, detail="An error occurred during the chat session.")