import os

from typing import Callable, Optional
from langchain_core.retrievers import BaseRetriever, Document
from pydantic import PrivateAttr
from openfga_sdk import ClientConfiguration, OpenFgaClient
from openfga_sdk.client.models import ClientCheckRequest
from openfga_sdk.sync import OpenFgaClient as OpenFgaClientSync
from openfga_sdk.credentials import CredentialConfiguration, Credentials


class FGARetriever(BaseRetriever):
    _retriever: BaseRetriever = PrivateAttr()
    _fga_configuration: ClientConfiguration = PrivateAttr()
    _query_builder: Callable[[Document], ClientCheckRequest] = PrivateAttr()

    def __init__(
        self,
        retriever: BaseRetriever,
        build_query: Callable[[Document], ClientCheckRequest],
        fga_configuration: Optional[ClientConfiguration] = None
    ):
        super().__init__()
        self._retriever = retriever
        self._fga_configuration = fga_configuration or ClientConfiguration(
            api_host=os.getenv('FGA_API_HOST') or "api.us1.fga.dev",
            store_id=os.getenv('FGA_STORE_ID'),
            credentials=Credentials(
                method="client_credentials",
                configuration=CredentialConfiguration(
                    api_issuer=os.getenv('FGA_API_ISSUER') or "auth.fga.dev",
                    api_audience=os.getenv(
                        'FGA_API_AUDIENCE') or "https://api.us1.fga.dev/",
                    client_id=os.getenv('FGA_CLIENT_ID'),
                    client_secret=os.getenv('FGA_CLIENT_SECRET')
                )
            )
        )
        self._query_builder = build_query

    async def _async_filter_FGA(self, docs: list[Document]):
        async with OpenFgaClient(self._fga_configuration) as fga_client:
            checks = [self._query_builder(doc) for doc in docs]
            results = await fga_client.batch_check(checks)
            await fga_client.close()
            return [doc for doc, result in zip(docs, results) if result.allowed]

    async def _aget_relevant_documents(self, query, *, run_manager):
        docs = await self._retriever._aget_relevant_documents(
            query, run_manager=run_manager)
        docs = await self._async_filter_FGA(docs)
        return docs

    def _filter_FGA(self, docs: list[Document]):
        with OpenFgaClientSync(self._fga_configuration) as fga_client:
            checks = [self._query_builder(doc) for doc in docs]
            results = fga_client.batch_check(checks)
            fga_client.close()
            return [doc for doc, result in zip(docs, results) if result.allowed]

    def _get_relevant_documents(self, query, *, run_manager):
        docs = self._retriever._get_relevant_documents(
            query, run_manager=run_manager)
        docs = self._filter_FGA(docs)
        return docs
