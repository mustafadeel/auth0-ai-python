import os
from typing import Callable, Optional
from llama_index.core.retrievers import BaseRetriever
from openfga_sdk import ClientConfiguration, OpenFgaClient
from openfga_sdk.client.models import ClientCheckRequest
from openfga_sdk.sync import OpenFgaClient as OpenFgaClientSync
from typing import List
from openfga_sdk.credentials import CredentialConfiguration, Credentials

from llama_index.core.schema import (
    Node,
    NodeWithScore,
    QueryBundle,
)


class FGARetriever(BaseRetriever):
    def __init__(
        self,
        retriever: BaseRetriever,
        build_query: Callable[[Node], ClientCheckRequest],
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

    def _filter_FGA(self, nodes: list[NodeWithScore]) -> List[NodeWithScore]:
        with OpenFgaClientSync(self._fga_configuration) as fga_client:
            checks = [self._query_builder(nodeWithScore.node)
                      for nodeWithScore in nodes]
            results = fga_client.batch_check(checks)
            fga_client.close()
            return [node for node, result in zip(nodes, results) if result.allowed]

    def _retrieve(self, query_bundle: QueryBundle) -> List[NodeWithScore]:
        """Retrieve nodes given query and filtered by FGA access.
        """
        nodes = self._retriever._retrieve(query_bundle)
        nodes = self._filter_FGA(nodes)
        return nodes

    async def _async_filter_FGA(self, nodes: list[NodeWithScore]) -> List[NodeWithScore]:
        async with OpenFgaClient(self._fga_configuration) as fga_client:
            checks = [self._query_builder(nodeWithScore.node)
                      for nodeWithScore in nodes]
            results = await fga_client.batch_check(checks)
            await fga_client.close()
            return [node for node, result in zip(nodes, results) if result.allowed]

    async def _aretrieve(self, query_bundle: QueryBundle) -> List[NodeWithScore]:
        """Retrieve nodes given query and filtered by FGA access.
        """
        nodes = await self._retriever._aretrieve(query_bundle)
        nodes = await self._async_filter_FGA(nodes)
        return nodes
