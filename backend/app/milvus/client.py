from pymilvus import connections, utility
from app.config import settings
import structlog

logger = structlog.get_logger()

def connect_milvus() -> None:
    """
    Establish a connection to the Milvus standalone instance.
    Utilizes PyMilvus' default connection pool.
    """
    try:
        # Check if "default" connection already exists
        if connections.has_connection("default"):
            logger.info("milvus_connection_already_exists")
            return
            
        connections.connect(
            alias="default",
            host=settings.MILVUS_HOST,
            port=settings.MILVUS_PORT
        )
        logger.info(
            "milvus_connected_successfully",
            host=settings.MILVUS_HOST,
            port=settings.MILVUS_PORT
        )
    except Exception as e:
        logger.error("milvus_connection_failed", host=settings.MILVUS_HOST, port=settings.MILVUS_PORT, error=str(e))
        raise e

def disconnect_milvus() -> None:
    """Disconnect from Milvus."""
    try:
        if connections.has_connection("default"):
            connections.disconnect("default")
            logger.info("milvus_disconnected_successfully")
    except Exception as e:
        logger.error("milvus_disconnect_failed", error=str(e))

def check_milvus_health() -> bool:
    """Check if the Milvus service is active and responsive."""
    try:
        if not connections.has_connection("default"):
            connections.connect(alias="default", host=settings.MILVUS_HOST, port=settings.MILVUS_PORT)
        
        # Test command (e.g. list collections or check server version)
        utility.list_collections()
        return True
    except Exception as e:
        logger.error("milvus_health_check_failed", error=str(e))
        return False
