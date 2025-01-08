# Auth0 AI for Python

> [!WARNING]
> Auth0 AI is currently under development and it is not intended to be used in production, and therefore has no official support.

[Auth0 AI](https://www.auth0.ai/) helps you build secure AI-powered
applications.

Developers are using LLMs to build generative AI applications that deliver
powerful new experiences for customers and employees. Maintaining security and
privacy while allowing AI agents to assist people in their work and lives is a
critical need. Auth0 AI helps you meet these requirements, ensuring that agents
are properly authorized when taking actions or accessing resources on behalf of
a person or organization. Common use cases include:

- **Authenticate users**: Easily implement login experiences, tailor made for
  AI agents and assistants.
- **Call APIs on users' behalf**: Use secure standards to call APIs from tools,
  integrating your app with other products.
- **Authorization for RAG**: Generate more relevant responses while ensuring
  that the agent is only incorporating information that the user has access to.
- **Async user confirmation**: Allow agents to operate autonomously in the
  background while requiring human approval when needed.

## Packages

- [`llama-index-auth0-ai`](./packages/llama-index-auth0-ai/) -
  Integration with [LlamaIndex](https://docs.llamaindex.ai/en/stable/) framework.

- [`langchain-auth0-ai`](./packages/langchain-auth0-ai/) -
  Integration with [Langchain](https://python.langchain.com/docs/tutorials/) framework.

## Running examples

Follow the steps below to set up and run the examples in the repository.

### Prerequisites

Ensure you have the following installed on your system:

- [Python](https://www.python.org/) 3.11 or later
- [Poetry](https://python-poetry.org/) for managing dependencies

### Steps to Run the Examples

1. Navigate to the [Example Folder](./examples/)
   Move to the `authorization-for-rag/langchain-rag` directory containing the sample code:

   ```sh
   $ cd examples/authorization-for-rag/langchain-rag/
   ```

2. Install Dependencies
   Use [Poetry](https://python-poetry.org/) to install the required dependencies:

   ```sh
   $ poetry install
   ```

3. Run the Example
   Execute the main script using Poetry:

   ```sh
   $ poetry run python langchain_rag/main.py
   ```

## Recommendations for VSCode Users

To streamline development with Poetry and virtual environments in VSCode, follow these steps:

1. Configure Poetry to Use In-Project Virtual Environments
   Run the following command to ensure the virtual environment is created within your project directory (e.g., .venv):

   ```bash
   poetry config virtualenvs.in-project true
   ```

2. Select the Correct Interpreter in VSCode

   - Open the Command Palette (Ctrl+Shift+P or Cmd+Shift+P).
   - Search for and select Python: Select Interpreter.
   - Choose the interpreter located in the .venv folder (e.g., .venv/bin/python).

## License

Apache-2.0
