"""
Filename    :   RAGManager.py
Copyright   :   FoundAItion Inc.
Description :   Image recognition
Written by  :   Alex Fedosov
Created     :   08/03/2023
Updated     :   08/03/2023
"""

from langchain.chains.qa_with_sources.retrieval import RetrievalQAWithSourcesChain
from langchain.chains.retrieval_qa.base import RetrievalQA
from langchain.callbacks import get_openai_callback
from langchain.callbacks.base import BaseCallbackHandler
from langchain.document_loaders import ConcurrentLoader
from langchain.document_loaders import RecursiveUrlLoader
from langchain.embeddings import OpenAIEmbeddings
from langchain.indexes import VectorstoreIndexCreator
from langchain.llms.openai import OpenAI
from langchain.vectorstores.chroma import Chroma

from bs4 import BeautifulSoup
from urllib.parse import urlparse, urlunparse

from typing import Dict, Union, Any, List

import chromadb
import logging
import os
import requests
import sys
 
log = logging.getLogger(__name__)


DEFAULT_SCHEME = "http"
DEFAULT_SCHEME_SECURE = "https"

def validate_url(url):
    if not url:
        return False, "Empty URL"
    
    parsed_url = urlparse(url)
    if not parsed_url.scheme and "." in parsed_url.path and " " not in parsed_url.path:
        url = DEFAULT_SCHEME_SECURE + "://" + url
        parsed_url = urlparse(url)

    scheme = parsed_url.scheme
    if scheme not in [DEFAULT_SCHEME, DEFAULT_SCHEME_SECURE]:
        scheme = DEFAULT_SCHEME_SECURE

    netloc = parsed_url.netloc
    if not netloc:
        return False, f"Invalid URL: missing net location in {url}"
    corrected_url = urlunparse((scheme, netloc, parsed_url.path, parsed_url.params, 
                                parsed_url.query, parsed_url.fragment))

    try:
        response = requests.get(corrected_url)
        if response.status_code < 400:
            return True, corrected_url
        return False, f"Can not reach web page {url}"
    except requests.RequestException as e:
        return False, f"Invalid web page {url}"


class CustomHandler(BaseCallbackHandler):
    def on_llm_start(
        self, serialized: Dict[str, Any], prompts: List[str], **kwargs: Any
    ) -> Any:
        log.debug(f"on_llm_start {prompts[0]}")

    def on_llm_error(
        self, error: Union[Exception, KeyboardInterrupt], **kwargs: Any
    ) -> Any:
        """Run when LLM errors."""
        log.debug(str(error))


class RAGManager():
    DEFAULT_DB_PATH = r".\fai-rag-db"
    DEFAULT_COLLECTION = "langchain"
    MAX_DOCS = 4  # documents loaded from vector store

    def __init__(self, ai_model, embedding_model, db_path=DEFAULT_DB_PATH) -> None:
        self.ai_model = ai_model
        self.embedding_model = embedding_model
        self.client = None
        self.chain = None
        self.llm = None
        self.vector_store = None
        self.handler = CustomHandler()
        self.db_path = db_path

    def _open(self) -> None:
        if self.client is None:
            self.client = chromadb.PersistentClient(self.db_path)
            log.debug(f"Database opened, {self.db_path=} ")

    def reset(self) -> int:
        """Clears existing database
        returns # of removed records
        """
        count = self.open()
        # NOTE: this would work for Chroma db only!
        collection = self.client.get_collection(RAGManager.DEFAULT_COLLECTION)
        collection.delete()
        log.debug(f"Database reset, {count} records removed")
        return count
    
    def _documents_count(self) -> int:
        """Count documents in database
        returns # of records in the database
        """
        if self.client is None:
            return 0

        # NOTE: this would work for Chroma db only!
        for collection in self.client.list_collections():
            if collection.name == RAGManager.DEFAULT_COLLECTION:
                return collection.count()
        return 0

    def open(self) -> int:
        """Just open existing database
        returns # of records in the database
        """
        if self.vector_store is None:
            self._open()
            embedding_function = OpenAIEmbeddings(model=self.embedding_model, request_timeout=20.0)
            self.vector_store = Chroma(client=self.client, embedding_function=embedding_function)

        return self._documents_count()

    def ingest_from_folder(self, data_folder_path) -> tuple((bool, str)):
        """Open or create database and load documents from folder
        returns True/False, ingestion status
        """
        base_name = os.path.basename(data_folder_path)
        dir_name = os.path.dirname(data_folder_path)
        
        if not os.path.exists(dir_name):
            return False, f"Folder {dir_name} does not exists"
        if not base_name:
            base_name = "**/*.*" # with subfolders
        elif not ("*" in base_name or "?" in base_name):
            return False, f"Invalid search pattern {base_name}"
        
        try:
            # TODO(afedosov):
            # define embeddings function so it's consistent for storage and query!
            self._open()

            documents_count = self._documents_count()
            loader = ConcurrentLoader.from_filesystem(dir_name, glob=base_name)
            index = VectorstoreIndexCreator(vectorstore_kwargs={"client": self.client}).from_loaders([loader])
            count = self._documents_count() - documents_count

            if count <= 0:
                return False, f"No documents found at {dir_name} or ingested before"

            self.vector_store = index.vectorstore
            log.debug(f"File documents ingested: {count=}")
            return True, f"{count}"
        except Exception as err:
            log.error(f"File documents ingestion exception: {err}")
            return False, str(err)
        
    def ingest_from_web(self, url_path, max_depth=2) -> tuple((bool, str)):
        """Open or create database and load documents from url
        returns True/False, ingestion status
        """

        # RecursiveUrlLoader requires fully formed url with schema
        ok, message = validate_url(url_path)
        if not ok:
            return False, message
        url_path = message

        def extractor(x):
            soup = BeautifulSoup(x)  # default "html.parser"
            if soup.is_xml:
                return ""
            return soup.text.strip()

        try:
            self._open()

            loader = RecursiveUrlLoader(url=url_path, max_depth=max_depth, extractor=extractor)
            docs = loader.load()
            docs_filtered = list(filter(lambda x:
                                        "css" not in x.metadata["source"] and
                                        "wp-json" not in x.metadata["source"], docs))
            if not docs_filtered:
                raise Exception("No pages found")
            
            count = len(docs_filtered)
            log.debug(f"Web documents extracted: {count}")

            index = VectorstoreIndexCreator(vectorstore_kwargs={"client": self.client}).from_documents(docs_filtered)
            self.vector_store = index.vectorstore

            log.debug(f"Web documents ingested: {count=}")
            return True, f"{count}"
        except Exception as err:
            log.error(f"Web documents ingestion exception: {err}")
            return False, str(err)
        
    def query(self, question) -> tuple((bool, str)):
        """ Query vector database
        returns closest record based on similarity
        """
        if self.vector_store is None:
            raise Exception("Assertion: ingestion failed, can't query")

        try:
            self.llm = self.llm or OpenAI(model_name=self.ai_model, 
                                          temperature=0, 
                                          max_retries=1,
                                          callbacks=[self.handler])

            # Curiously enough the result of RetrievalQAWithSourcesChain call may differ
            # from RetrievalQA with return_source_documents=True           
            retriever = self.vector_store.as_retriever()
            retriever.search_kwargs['k'] = RAGManager.MAX_DOCS
            retriever.search_kwargs['fetch_k'] = RAGManager.MAX_DOCS

            self.chain = self.chain or RetrievalQAWithSourcesChain.from_chain_type(
                self.llm,  
                retriever=retriever,
                verbose=False
                )

            # Langchain actually combines vector db search result with prompt question and 
            # sends it to LLM for final answer compostion
            with get_openai_callback() as cb:
                answer = self.chain(question)
                log.debug(f"RAG query, tokens used: {cb.total_tokens}")
                
            log.debug(f"RAG query complete: {answer}")
            return True, answer
        except Exception as err:
            log.error(f"RAG query exception: {err}")
            return False, str(err)
