import os
from fastapi import HTTPException
from elasticsearch import AsyncElasticsearch, exceptions as es_exceptions
from dotenv import load_dotenv
from common.logging import setup_logger

load_dotenv()
logger = setup_logger()


def get_es_client():
    es_host = os.getenv("ES_HOST")
    es_port = os.getenv("ES_PORT")
    if not es_host or not es_port:
        logger.error("Missing Elasticsearch host or port configuration.")
        raise ValueError("ES_HOST and ES_PORT must be set in the environment.")
    
    logger.info(f"Connecting to Elasticsearch at {es_host}:{es_port}")
    client = AsyncElasticsearch(
        hosts=[f"{es_host}:{es_port}"],
        max_retries=10,
        retry_on_timeout=True,
        request_timeout=120
    )
    return client


class ElasticsearchServiceError(Exception):
    pass

class ElasticsearchConnectionError(ElasticsearchServiceError):
    pass

class ElasticsearchRequestError(ElasticsearchServiceError):
    pass


class ElasticsearchService:

    def __init__(self, es_client=None):
        self.es = es_client or get_es_client()

    async def _validate_timeout(self, timeout):
        if isinstance(timeout, str):
            if timeout.endswith("s"):
                timeout = timeout[:-1]
            try:
                timeout = float(timeout)
            except ValueError:
                raise ValueError("Timeout value must be a number or a string ending with 's'.")
        elif not isinstance(timeout, (int, float)):
            raise ValueError("Timeout value must be a number.")
        return timeout

    async def search_logs(self, index, query, size=5, sort_field="@timestamp", sort_order="desc", timeout="30s"):
        try:
            timeout = await self._validate_timeout(timeout)

            response = await self.es.search(
                index=index,
                body={"size": size, "sort": [{sort_field: {"order": sort_order}}], "query": query},
                request_timeout=timeout,
            )
            return [hit["_source"] for hit in response.get("hits", {}).get("hits", [])]
        except es_exceptions.ConnectionError as e:
            raise ElasticsearchConnectionError(f"Connection error while searching logs: {str(e)}")
        except es_exceptions.RequestError as e:
            raise ElasticsearchRequestError(f"Request error while searching logs: {str(e)}")
        except Exception as e:
            raise ElasticsearchServiceError(f"Unexpected error while searching logs: {str(e)}")

    async def save_document(self, index, doc_id, body, overwrite=False, timeout="30s"):
        try:
            timeout = await self._validate_timeout(timeout)

            if not await self.es.indices.exists(index=index):
                await self.es.indices.create(
                    index=index,
                    body={
                        "settings": {
                            "number_of_shards": 1,
                            "number_of_replicas": 1
                        }
                    }
                )
                logger.info(f"Index '{index}' created.")

            if not overwrite and await self.es.exists(index=index, id=doc_id):
                existing_doc = await self.es.get(index=index, id=doc_id)
                if existing_doc['_source'] == body:
                    logger.info(f"Document with ID '{doc_id}' already exists with same content. Skipping save.")
                    return

            await self.es.index(index=index, id=doc_id, body=body, request_timeout=timeout)
            logger.info(f"Document with ID '{doc_id}' saved to index '{index}'.")
        except es_exceptions.ConnectionError as e:
            raise ElasticsearchConnectionError(f"Connection error while saving document: {str(e)}")
        except es_exceptions.RequestError as e:
            raise ElasticsearchRequestError(f"Request error while saving document: {str(e)}")
        except Exception as e:
            raise ElasticsearchServiceError(f"Unexpected error while saving document: {str(e)}")

    async def delete_document(self, index, doc_id, timeout="30s"):
        try:
            timeout = await self._validate_timeout(timeout)

            if not await self.es.indices.exists(index=index):
                logger.warning(f"Index '{index}' does not exist. Skipping deletion.")
                return
            
            if not await self.es.exists(index=index, id=doc_id):
                logger.warning(f"Document with ID '{doc_id}' does not exist in index '{index}'. Skipping deletion.")
                return

            await self.es.delete(index=index, id=doc_id, request_timeout=timeout)
            logger.info(f"Document with ID '{doc_id}' deleted from index '{index}'.")
        except es_exceptions.ConnectionError as e:
            raise ElasticsearchConnectionError(f"Connection error while deleting document: {str(e)}")
        except es_exceptions.RequestError as e:
            raise ElasticsearchRequestError(f"Request error while deleting document: {str(e)}")
        except Exception as e:
            raise ElasticsearchServiceError(f"Unexpected error while deleting document: {str(e)}")

    async def close_connection(self):
        try:
            await self.es.close()
            logger.info("Elasticsearch connection closed successfully.")
        except Exception as e:
            logger.warning(f"Error while closing Elasticsearch connection: {str(e)}")
