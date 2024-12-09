import os
from fastapi import HTTPException
from elasticsearch import Elasticsearch, exceptions as es_exceptions
from dotenv import load_dotenv
from common.logging import setup_logger

load_dotenv()
logger = setup_logger()

def get_es_client():
    es_host = os.getenv("ES_HOST")
    es_port = os.getenv("ES_PORT")
    client = Elasticsearch(f"{es_host}:{es_port}", max_retries=10, retry_on_timeout=True, request_timeout=120)
    try:
        if not client.ping():
            raise es_exceptions.ConnectionError("Elasticsearch connection failed.")
    except es_exceptions.ConnectionError as e:
        logger.error(f"Failed to connect to Elasticsearch: {str(e)}")
        raise
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

    def search_logs(self, index, query, size=5, sort_field="@timestamp", sort_order="desc"):
        try:
            response = self.es.search(
                index=index,
                body={"size": size, "sort": [{sort_field: {"order": sort_order}}], "query": query},
                timeout="30s",
            )
            return [hit["_source"] for hit in response.get("hits", {}).get("hits", [])]
        except es_exceptions.ConnectionError as e:
            raise ElasticsearchConnectionError(f"Connection error while searching logs: {str(e)}")
        except es_exceptions.RequestError as e:
            raise ElasticsearchRequestError(f"Request error while searching logs: {str(e)}")
        except Exception as e:
            raise ElasticsearchServiceError(f"Unexpected error while searching logs: {str(e)}")

    def save_document(self, index, doc_id, body, overwrite=False):
        try:
            if not overwrite and self.es.exists(index=index, id=doc_id):
                logger.warning(f"Document with ID '{doc_id}' already exists in index '{index}'. Skipping save.")
                return
            self.es.index(index=index, id=doc_id, body=body)
            logger.info(f"Document with ID '{doc_id}' saved to index '{index}'.")
        except es_exceptions.ConnectionError as e:
            raise ElasticsearchConnectionError(f"Connection error while saving document: {str(e)}")
        except es_exceptions.RequestError as e:
            raise ElasticsearchRequestError(f"Request error while saving document: {str(e)}")
        except Exception as e:
            raise ElasticsearchServiceError(f"Unexpected error while saving document: {str(e)}")