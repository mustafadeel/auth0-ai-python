## Authorization for RAG with Okta FGA

Authorization for RAG ensure that users can only access documents they are permitted to view. By enforcing strict access controls during the document retrieval process, it prevents unauthorized data exposure and maintains data security. For more information, refer to the Authorization for RAG [documentation](https://demo.auth0.ai/docs/authorization-for-rag).

### How It Works

1. **User Query**: A user submits a query requiring information retrieval.
2. **Document Retrieval**: The system employs a retriever to search its vector store for documents relevant to the query.
3. **Authorization Check**: Auth0 FGA verifies the user's permissions, filtering out any documents the user is not authorized to access.
4. **Response Generation**: Based on the authorized documents, the system generates a response tailored to the user's access level.

### Examples

Explore the following examples demonstrating the integration of Auth0 FGA with LangChain and LlamaIndex retrievers:

- **LangChain with FGARetriever**: An implementation showcasing how to wrap a LangChain retriever with FGARetriever to enforce authorization checks during document retrieval.
- **LlamaIndex with FGARetriever**: A sample application illustrating the use of FGARetriever with LlamaIndex to ensure users can only access permitted documents.

By following these examples, you can implement fine-grained authorization in your RAG applications, ensuring secure and compliant data access for your users.
