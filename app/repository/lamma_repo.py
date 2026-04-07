from llama_index.core import SimpleDirectoryReader, StorageContext
from llama_index.core.indices.multi_modal.base import MultiModalVectorStoreIndex
from qdrant_client import QdrantClient
from llama_index.vector_stores.qdrant import QdrantVectorStore
from qdrant_client.http.models import Distance, VectorParams
from llama_index.readers.file import ImageReader, FlatReader
from app.config.env_config import settings
from llama_index.embeddings.clip import ClipEmbedding
from llama_index.core.node_parser import TokenTextSplitter
from app.constants.app_constants import VECTOR_DB
from llama_index.core.vector_stores import MetadataFilters, ExactMatchFilter

class LammaRepository:
    """Qdrant vector database using lamma index"""

    def __init__(self,host = settings.QDRANT_HOST, port=settings.QDRANT_PORT):
        """Intilizing the data needed for the Multimodel vector store"""
        self.client = QdrantClient(host=host,port=port)
        self.embed_model = ClipEmbedding()

        if not self.client.collection_exists(VECTOR_DB.MULTIMODAL_TEXT_COLLECTION_NAME.value):
            self.client.create_collection(
                collection_name=VECTOR_DB.MULTIMODAL_TEXT_COLLECTION_NAME.value,
                vectors_config=VectorParams(size=1536, distance=Distance.COSINE),
            )
    
        if not self.client.collection_exists(VECTOR_DB.MULTIMODAL_IMAGE_COLLECTION_NAME.value):
            self.client.create_collection(
                collection_name=VECTOR_DB.MULTIMODAL_IMAGE_COLLECTION_NAME.value,
                vectors_config=VectorParams(size=512, distance=Distance.COSINE),
            )

        self.image_store = QdrantVectorStore(
            client= self.client,
            collection_name= VECTOR_DB.MULTIMODAL_IMAGE_COLLECTION_NAME.value
        )

        self.text_store = QdrantVectorStore(
            client=self.client,
            collection_name= VECTOR_DB.MULTIMODAL_TEXT_COLLECTION_NAME.value
        )

        self.storage_context = StorageContext.from_defaults(
            image_store = self.image_store,
            vector_store = self.text_store
        )

        self.image_reader = ImageReader()
        self.text_reader = FlatReader()
        
        self.index = MultiModalVectorStoreIndex.from_vector_store(
            image_vector_store=self.image_store,
            vector_store=self.text_store
        )

    def add_data_to_qdrant(self, frame_input_path:str, srt_path: str):
        
        image_docs = SimpleDirectoryReader(
            input_dir=frame_input_path,
            file_extractor={".jpg": ImageReader(), ".png": ImageReader(), ".jpeg": ImageReader()},
            recursive=True
        ).load_data()

        srt_docs = SimpleDirectoryReader(
            input_files=[srt_path],
            file_extractor={".srt": FlatReader()}, 
            recursive=True,
        ).load_data()

        splitter = TokenTextSplitter(chunk_size=300, chunk_overlap=50)
        srt_nodes = splitter.get_nodes_from_documents(srt_docs)
        all_docs = image_docs + srt_nodes

        index = MultiModalVectorStoreIndex.from_documents(
            all_docs,
            storage_context=self.storage_context,
            image_embed_model=self.embed_model
        )

        return index


    def get_index(self):
        """Get THE Index of the multi modal vector
        
        Returns:
            gives the object of MultiModalVectorStoreIndex vector store
        """
        return MultiModalVectorStoreIndex.from_vector_store(
            image_vector_store=self.image_store,
            vector_store=self.text_store,
            image_embed_model=self.embed_model
        )
    
    def get_query_engine(self, video_id: str):
        """"""
        index = self.get_index()
        filters = MetadataFilters(
            filters=[
                ExactMatchFilter(key="filename", value=f"{video_id}.en.srt")
            ]
        )
        return index.as_query_engine(
            filters=filters,
            similarity_top_k=3,
            image_similarity_top_k=3
        )


