Vector Store (Pinecone) & Object Storage (AWS S3)
Project 4 — Infrastructure Layer Extension
Architecture: Hexagonal Architecture (Ports & Adapters)
Integrations: Pinecone Serverless & Amazon S3
Status: Infrastructure adapters implemented; ingestion and retrieval workflows planned for the next milestone.
Table of Contents
Executive Summary
Objectives and Scope
Technology Stack
Architecture Overview
Project Structure
Core Architecture Components
Vector Store Integration — Pinecone
Object Storage Integration — AWS S3
Provider Factory and Dependency Injection
Configuration Reference
Document Ingestion Workflow
Document Retrieval Workflow
Installation and Setup
Index Provisioning
Testing and Validation
Error Handling and Exception Management
Troubleshooting Guide
Security and Production Considerations
Performance and Scalability
Implementation Roadmap
Architecture Decisions
Conclusion
1. Executive Summary

This infrastructure extension introduces two external services into the application architecture:

Pinecone: A managed vector database responsible for storing and retrieving high-dimensional embedding vectors.
Amazon S3: An object storage service responsible for storing original uploaded documents and other binary assets.

Both integrations follow the application's existing Hexagonal Architecture (Ports & Adapters) pattern, ensuring that external infrastructure dependencies remain isolated from business logic.

Instead of allowing application services to communicate directly with Pinecone or AWS SDKs, the application interacts through vendor-neutral interfaces.

This architecture provides:

Infrastructure abstraction and loose coupling.
Independent replacement of infrastructure providers.
Centralized provider construction and configuration.
Easier unit testing and integration testing.
Improved maintainability and extensibility.
A foundation for Retrieval-Augmented Generation (RAG).
1.1 High-Level Architecture
mermaid
flowchart TB
    APP["Application Layer"]

    subgraph CORE["Application Core"]
        VP["BaseVectorStore"]
        SP["BaseStorage"]
        EMB["BaseEmbeddings"]
    end

    subgraph INFRA["Infrastructure Layer"]
        PF["Vector Store Factory"]
        SF["Storage Factory"]
        PA["Pinecone Adapter"]
        SA["AWS S3 Adapter"]
    end

    subgraph PROVIDERS["External Providers"]
        PC[("Pinecone Serverless")]
        S3[("Amazon S3")]
        VE["Vercel AI Gateway"]
    end

    APP --> VP
    APP --> SP
    APP --> EMB

    VP --> PF
    SP --> SF

    PF --> PA
    SF --> SA

    PA --> PC
    SA --> S3
    EMB --> VE

1.2 Integration Responsibilities
Component	Responsibility
Pinecone	Vector storage and similarity search
AWS S3	Original document and binary object storage
BaseVectorStore	Vendor-neutral vector database contract
BaseStorage	Vendor-neutral object storage contract
Provider Factories	Provider registration and construction
Dependency Injection	Centralized application-level provider access
AppSettings	Infrastructure configuration management
2. Objectives and Scope
2.1 Objectives

The primary objective is to introduce scalable infrastructure services without compromising the existing application architecture.

Specific objectives include:

Introduce a generic vector database abstraction.
Implement Pinecone as the first vector database adapter.
Introduce a generic object storage abstraction.
Implement AWS S3 as the first object storage adapter.
Provide centralized provider factories.
Integrate both providers into the application's dependency injection system.
Centralize provider configuration.
Support integration testing through smoke-test scripts.
Prepare the infrastructure for document ingestion and semantic retrieval.
2.2 Current Scope
Feature	Status
Vector store interface	Implemented
Storage interface	Implemented
Pinecone adapter	Implemented
AWS S3 adapter	Implemented
Vector store factory	Implemented
Storage factory	Implemented
Dependency injection	Implemented
Environment configuration	Implemented
Pinecone index provisioning script	Implemented
S3 smoke testing	Implemented
Pinecone smoke testing	Implemented
Document ingestion orchestration	Planned
Document retrieval orchestration	Planned
Reranking integration	Planned
3. Technology Stack
Technology	Purpose
Python	Application implementation
Pydantic Settings	Configuration management
Pinecone	Vector database
Pinecone Python SDK	Vector database communication
AWS S3	Object storage
boto3	AWS SDK for Python
botocore	AWS client configuration
Cohere Embed v4	Embedding generation
Vercel AI Gateway	Embedding provider access
PostgreSQL	Document metadata and application persistence
Mermaid	Architecture and workflow visualization
3.1 External Infrastructure
Pinecone Serverless

Pinecone provides managed vector storage and similarity search.

The application uses the classic vector API with client-generated embeddings.

Amazon S3

Amazon S3 provides durable object storage for uploaded documents.

Original documents are stored independently of their extracted text, chunks, and embedding vectors.

4. Architecture Overview

The implementation follows Hexagonal Architecture, also known as Ports and Adapters.

The fundamental principle is that the application core should not depend directly on external infrastructure SDKs.

Instead, infrastructure services implement interfaces defined inside the application.

4.1 Ports and Adapters
mermaid
flowchart LR
    subgraph APPLICATION["Application Core"]
        A["Application Services"]
        B["BaseVectorStore"]
        C["BaseStorage"]
    end

    subgraph ADAPTERS["Infrastructure Adapters"]
        D["PineconeVectorStore"]
        E["S3Storage"]
    end

    subgraph EXTERNAL["External Infrastructure"]
        F[("Pinecone")]
        G[("AWS S3")]
    end

    A --> B
    A --> C

    D -. implements .-> B
    E -. implements .-> C

    D --> F
    E --> G

4.2 Architectural Principles
Dependency Inversion

Application services depend on abstractions rather than concrete infrastructure implementations.

Separation of Concerns

Each component has a focused responsibility:

Interfaces define contracts.
Adapters implement external communication.
Factories construct provider instances.
Dependency injection exposes providers to application services.
Configuration controls provider selection.
Provider Independence

The application should not require changes to its business logic when replacing Pinecone or S3 with alternative providers.

For example:

text
BaseVectorStore
    |
    +-- PineconeVectorStore
    |
    +-- QdrantVectorStore (future)
    |
    +-- WeaviateVectorStore (future)


Similarly:

text
BaseStorage
    |
    +-- S3Storage
    |
    +-- AzureBlobStorage (future)
    |
    +-- GoogleCloudStorage (future)


These additional providers are architectural extension possibilities, not currently implemented adapters.

5. Project Structure

The following files and directories are involved in this infrastructure extension.

text
project/
│
├── src/
│   └── app/
│       │
│       ├── application/
│       │   └── dependencies/
│       │       └── providers.py
│       │
│       ├── core/
│       │   ├── config.py
│       │   └── exceptions.py
│       │
│       └── domains/
│           │
│           ├── interfaces/
│           │   ├── vector_store.py
│           │   └── storage.py
│           │
│           └── infrastructure/
│               │
│               ├── vector_store/
│               │   ├── __init__.py
│               │   ├── pinecone.py
│               │   └── factory.py
│               │
│               └── storage/
│                   ├── __init__.py
│                   ├── s3.py
│                   └── factory.py
│
├── scripts/
│   ├── create_pinecone_index.py
│   └── smoke_vector_and_s3.py
│
├── .env
├── .env.example
└── VECTOR_STORE_AND_OBJECT_STORAGE.md

5.1 File Responsibilities
File	Layer	Responsibility
interfaces/vector_store.py	Port	Vector database abstraction
interfaces/storage.py	Port	Object storage abstraction
infrastructure/vector_store/pinecone.py	Adapter	Pinecone implementation
infrastructure/storage/s3.py	Adapter	S3 implementation
infrastructure/vector_store/factory.py	Factory	Vector provider construction
infrastructure/storage/factory.py	Factory	Storage provider construction
application/dependencies/providers.py	Composition	Cached provider dependencies
core/config.py	Configuration	Provider and infrastructure settings
core/exceptions.py	Core	Infrastructure exception definitions
create_pinecone_index.py	Script	Pinecone index provisioning
smoke_vector_and_s3.py	Script	Integration validation
6. Core Architecture Components
6.1 BaseVectorStore

Location:

text
src/app/domains/interfaces/vector_store.py


This interface defines the contract that every vector database provider must implement.

Responsibilities
Store embedding vectors.
Retrieve semantically similar vectors.
Delete vectors using metadata filters.
Expose vector database statistics.
Contract
python
class BaseVectorStore:

    def upsert(
        self,
        ids,
        vectors,
        metadatas
    ) -> int:
        ...

    def query(
        self,
        vector,
        top_k=4,
        filter=None
    ) -> list:
        ...

    def delete_by_filter(
        self,
        filter
    ) -> None:
        ...

    def stats(self) -> dict:
        ...


The code above represents the documented contract; the actual implementation remains defined in the project interface.

Method Reference
Method	Input	Output	Purpose
upsert	IDs, vectors, metadata	Integer	Insert or update vectors
query	Query vector, top_k, filter	List	Similarity search
delete_by_filter	Metadata filter	None	Delete matching vectors
stats	None	Dictionary	Index statistics
Expected Query Result
python
[
    {
        "id": "document-001-chunk-0001",
        "score": 0.98,
        "metadata": {
            "doc_id": "document-001",
            "chunk_index": 0,
            "text": "Example document content."
        }
    }
]


The actual result structure should remain consistent with the adapter's implementation.

6.2 BaseStorage

Location:

text
src/app/domains/interfaces/storage.py


This interface defines a provider-neutral contract for object storage.

Contract
python
class BaseStorage:

    def put(
        self,
        key,
        data,
        content_type
    ) -> str:
        ...

    def get(
        self,
        key
    ) -> bytes:
        ...

    def delete(
        self,
        key
    ) -> None:
        ...

    def presigned_url(
        self,
        key,
        expires_in=None
    ) -> str:
        ...

Method Reference
Method	Input	Output	Purpose
put	Key, binary data, content type	String	Upload object
get	Object key	Bytes	Download object
delete	Object key	None	Delete object
presigned_url	Key, optional expiry	String	Generate temporary GET URL
Object Naming Convention
text
documents/
    {doc_id}/
        source.pdf

smoke/
    test-{timestamp}.txt


This structure separates application documents from temporary integration-test objects.

7. Vector Store Integration — Pinecone

Adapter:

text
src/app/domains/infrastructure/vector_store/pinecone.py

7.1 Overview

The Pinecone adapter implements BaseVectorStore using Pinecone's classic vectors API.

The application generates embeddings externally and sends the resulting vectors to Pinecone.

This keeps embedding generation independent of the vector database.

7.2 Integration Architecture
mermaid
flowchart TB
    A["Application Service"]
    B["BaseVectorStore"]
    C["PineconeVectorStore"]
    D["Pinecone Python SDK"]
    E[("Pinecone Serverless Index")]

    A --> B
    B --> C
    C --> D
    D --> E

7.3 Connection Configuration

The adapter connects using:

text
PINECONE_API_KEY
PINECONE_INDEX_HOST


The index host must be the complete URL supplied by the Pinecone console.

Example:

env
PINECONE_INDEX_HOST=https://your-index-host.svc.ap-southeast-1.aws.pinecone.io


Serverless indexes are host-addressed.

PINECONE_ENVIRONMENT is a legacy setting and is not used by this implementation.

7.4 Vector Dimension

The configured dimension is:

env
PINECONE_DIMENSION=1024


This must match the embedding model's output dimension.

The current embedding configuration uses:

text
Provider: Vercel AI Gateway
Model: cohere/embed-v4.0
Dimension: 1024


A dimension mismatch between the embedding model and Pinecone index will cause vector write or query failures.

7.5 Upsert Batching

The adapter processes vectors in batches of 100.

mermaid
flowchart TD
    A["Incoming Vectors"] --> B["Prepare Vector Records"]
    B --> C["Batch Size: 100"]
    C --> D["Pinecone Upsert"]
    D --> E{"More Batches?"}
    E -->|Yes| C
    E -->|No| F["Return Total Upserted"]


Batching helps control request sizes and makes large ingestion workloads easier to manage.

The appropriate batch size should be validated against vector dimensions and metadata payload sizes.

7.6 Metadata Structure

Each vector can contain metadata such as:

json
{
  "doc_id": "document-001",
  "chunk_index": 0,
  "text": "Extracted document content."
}


Metadata supports:

Document-level filtering.
Chunk identification.
Retrieval context construction.
Document-level deletion.

Avoid storing unnecessary or excessively large metadata payloads.

7.7 Namespace Support

Optional namespace configuration:

env
PINECONE_NAMESPACE=""


An empty namespace uses the default namespace.

Namespaces can later support logical isolation between tenants, environments, or collections, provided the application consistently applies the intended namespace.

7.8 Delete by Metadata Filter

Example:

python
{
    "doc_id": {
        "$eq": "document-001"
    }
}


This enables deletion of all vectors belonging to a particular document.

The implementation requires a compatible serverless index using the classic vector API.

7.9 Index Statistics

The adapter exposes index statistics through:

python
vector_store.stats()


Example:

python
{
    "dimension": 1024,
    "metric": "cosine",
    "total_vector_count": 100
}


Actual statistics depend on the index and its current state.

8. Object Storage Integration — AWS S3

Adapter:

text
src/app/domains/infrastructure/storage/s3.py

8.1 Overview

The S3 adapter implements BaseStorage using the AWS SDK for Python (boto3).

It provides a consistent application-level interface for object storage operations.

8.2 Integration Architecture
mermaid
flowchart TB
    A["Application Service"]
    B["BaseStorage"]
    C["S3Storage"]
    D["boto3 S3 Client"]
    E[("AWS S3 Bucket")]

    A --> B
    B --> C
    C --> D
    D --> E

8.3 Supported Operations
Upload
python
storage.put(
    key="documents/doc-001/source.pdf",
    data=file_bytes,
    content_type="application/pdf"
)


Returns a storage URI in the form:

text
s3://bucket-name/documents/doc-001/source.pdf

Download
python
content = storage.get(
    key="documents/doc-001/source.pdf"
)


Returns binary content.

Delete
python
storage.delete(
    key="documents/doc-001/source.pdf"
)


Deletes the specified object.

Presigned URL
python
url = storage.presigned_url(
    key="documents/doc-001/source.pdf",
    expires_in=3600
)


Generates a temporary GET URL.

8.4 Presigned URL Configuration

The implementation uses AWS Signature Version 4:

python
botocore.config.Config(
    signature_version="s3v4"
)


The default expiry is configured through:

env
S3_PRESIGN_EXPIRY=3600


This represents a one-hour URL lifetime.

Presigned URLs should be treated as bearer credentials: anyone possessing a valid URL may access the associated object until it expires or becomes invalid.

8.5 AWS Authentication

AWS credentials are optional in the application environment.

When explicit credentials are not provided, boto3 can use its standard credential resolution chain, including:

Environment variables.
Shared AWS credentials configuration.
AWS IAM roles.
Supported workload identity mechanisms.

For production workloads, IAM roles or equivalent workload identity mechanisms are preferable to long-lived access keys.

9. Provider Factory and Dependency Injection
9.1 Factory Pattern

Factories centralize the creation of infrastructure providers.

The application requests a provider through a shared construction interface rather than instantiating vendor SDK clients directly.

Vector Store Factory
text
src/app/domains/infrastructure/vector_store/factory.py

Storage Factory
text
src/app/domains/infrastructure/storage/factory.py


Both factories use a provider registry and a shared build_provider() construction pattern.

9.2 Provider Resolution
mermaid
flowchart TD
    A["Application Configuration"] --> B["Read Provider Name"]

    B --> C{"Provider Type"}

    C -->|pinecone| D["Vector Store Factory"]
    C -->|aws| E["Storage Factory"]

    D --> F["Pinecone Adapter"]
    E --> G["S3 Adapter"]

    F --> H["BaseVectorStore Instance"]
    G --> I["BaseStorage Instance"]

9.3 Dependency Injection

Location:

text
src/app/application/dependencies/providers.py


The composition root exposes:

python
get_vector_store()
get_storage()


Both dependencies use caching through lru_cache.

Responsibilities
Construct infrastructure providers.
Centralize application-level provider access.
Avoid repeated client construction.
Keep infrastructure selection outside business logic.
9.4 Cache Management

Provider caching improves resource reuse.

During tests, provider-dependent test cases may need fresh dependencies.

The application exposes or uses:

python
reset_all_caches()


This should be integrated into relevant test fixtures so that provider configuration changes are not hidden by previously cached instances.

10. Configuration Reference

Configuration is centralized in:

text
src/app/core/config.py


The application uses environment-based configuration through AppSettings.

10.1 Pinecone Configuration
env
# Vector Store Provider
VECTOR_STORE_PROVIDER="pinecone"

# Pinecone Credentials
PINECONE_API_KEY="pcsk_..."

# Pinecone Serverless Index
PINECONE_INDEX_HOST="https://your-index-host.svc.ap-southeast-1.aws.pinecone.io"

# Optional Namespace
PINECONE_NAMESPACE=""

# Index Region
PINECONE_REGION="ap-southeast-1"

# Embedding Dimension
PINECONE_DIMENSION=1024

10.2 AWS S3 Configuration
env
# Storage Provider
STORAGE_PROVIDER="aws"

# AWS Credentials
AWS_ACCESS_KEY_ID="..."
AWS_SECRET_ACCESS_KEY="..."

# AWS Region
AWS_REGION="ap-south-1"

# S3 Bucket
AWS_S3_BUCKET_NAME="your-bucket-name"

# Presigned URL Expiration
S3_PRESIGN_EXPIRY=3600

10.3 Configuration Reference Table
Variable	Required	Description
VECTOR_STORE_PROVIDER	Yes	Vector provider selection
PINECONE_API_KEY	Yes	Pinecone authentication
PINECONE_INDEX_HOST	Yes	Full Pinecone index URL
PINECONE_NAMESPACE	No	Vector namespace
PINECONE_REGION	Configuration-dependent	Pinecone index region
PINECONE_DIMENSION	Yes	Vector dimensionality
STORAGE_PROVIDER	Yes	Storage provider selection
AWS_ACCESS_KEY_ID	No	Explicit AWS access key
AWS_SECRET_ACCESS_KEY	No	Explicit AWS secret key
AWS_REGION	Yes	S3 bucket region
AWS_S3_BUCKET_NAME	Yes	Target bucket
S3_PRESIGN_EXPIRY	No	Presigned URL expiry in seconds

The exact required-field validation is determined by the project's AppSettings implementation.

10.4 AppSettings Extensions

The new settings include:

text
vector_store_provider
storage_provider
PineconeSettings.namespace
AWSSettings.presign_expiry


Defaults:

text
vector_store_provider = pinecone
storage_provider = aws

10.5 Environment Configuration Rules
Never commit .env files containing credentials.
Maintain a .env.example with placeholder values.
Ensure Pinecone dimension matches the embedding model.
Ensure Pinecone region matches the provisioned index.
Ensure AWS region matches the S3 bucket.
Validate the full Pinecone index host.
Avoid storing production credentials in source control.
11. Document Ingestion Workflow
11.1 Overview

The ingestion workflow will connect document upload, object storage, text extraction, chunking, embedding generation, vector indexing, and PostgreSQL metadata updates.

The workflow is planned for the next implementation milestone.

11.2 End-to-End Pipeline
mermaid
flowchart TD
    A["User Uploads Document"]
    B["Validate Document"]
    C["Upload Original to S3"]
    D["Extract Text"]
    E["Split into Chunks"]
    F["Generate Embeddings"]
    G["Upsert Vectors to Pinecone"]
    H["Update PostgreSQL"]
    I["Mark Document READY"]

    A --> B
    B --> C
    C --> D
    D --> E
    E --> F
    F --> G
    G --> H
    H --> I

    B -->|Invalid| X["Validation Error"]
    C -->|Failure| Y["Storage Error"]
    D -->|Failure| Z["Extraction Error"]
    F -->|Failure| W["Embedding Error"]
    G -->|Failure| V["Vector Store Error"]

11.3 Detailed Processing Steps
Step 1: Document Upload

Receive the uploaded file and validate its basic properties.

Step 2: Store Original File

Upload the original file to S3.

Suggested key:

text
documents/{doc_id}/source.ext

Step 3: Text Extraction

Extract text using the relevant document parser.

Potential formats include:

PDF
DOCX
TXT
Other supported document formats
Step 4: Chunking

Split extracted text into smaller overlapping segments.

Configuration:

text
CHUNK_SIZE
CHUNK_OVERLAP


Chunking is important because embedding models and retrieval systems work with bounded text segments.

Step 5: Embedding Generation

Generate embeddings through the existing embedding abstraction.

text
Provider: Vercel AI Gateway
Model: cohere/embed-v4.0
Dimension: 1024

Step 6: Pinecone Upsert

Store vectors with associated metadata.

Example:

json
{
  "doc_id": "document-001",
  "chunk_index": 0,
  "text": "Extracted document chunk."
}

Step 7: PostgreSQL Update

After successful indexing, update the document record:

text
documents.status = "ready"


The document should not be marked ready before the required ingestion operations have completed successfully.

11.4 Suggested Ingestion State Model
mermaid
stateDiagram-v2
    [*] --> uploaded
    uploaded --> processing
    processing --> chunking
    chunking --> embedding
    embedding --> indexing
    indexing --> ready

    uploaded --> failed
    processing --> failed
    chunking --> failed
    embedding --> failed
    indexing --> failed

    ready --> [*]
    failed --> [*]


This is a proposed workflow state model, not a claim about currently implemented PostgreSQL state transitions.

12. Document Retrieval Workflow
12.1 Overview

The retrieval workflow performs semantic similarity search against Pinecone and prepares relevant document chunks for LLM context generation.

12.2 Retrieval Architecture
mermaid
flowchart TD
    A["User Query"]
    B["Generate Query Embedding"]
    C["Pinecone Query"]
    D["Top-K Similarity Results"]
    E{"Reranking Enabled?"}
    F["Rerank Results"]
    G["Build Context"]
    H["Send Context to LLM"]
    I["Generate Response"]

    A --> B
    B --> C
    C --> D
    D --> E
    E -->|Yes| F
    E -->|No| G
    F --> G
    G --> H
    H --> I

12.3 Retrieval Steps
Receive the user's query.
Generate a query embedding.
Execute Pinecone similarity search.
Retrieve the configured number of matching chunks.
Apply metadata filters where needed.
Optionally rerank retrieved results.
Construct the LLM context.
Generate the final response.
12.4 Top-K Retrieval

The vector store interface provides:

python
query(
    vector=query_embedding,
    top_k=4,
    filter=None
)


The top_k parameter controls the maximum number of matching vectors requested.

Its optimal value should be evaluated against retrieval quality, latency, and context-window constraints.

12.5 Document-Level Filtering

Example:

python
{
    "doc_id": {
        "$eq": "document-001"
    }
}


This allows retrieval to be restricted to a particular document.

13. Installation and Setup
13.1 Install Dependencies

Install the required packages:

bash
pip install pinecone boto3


If the project manages dependencies through a requirements file or package manager, add the dependencies to that existing dependency configuration as well.

13.2 Configure Environment Variables

Create or update the environment file:

bash
cp .env.example .env


Configure the Pinecone and AWS values.

13.3 Validate AWS Configuration

Check that the configured AWS identity can access the target bucket.

For example:

bash
aws sts get-caller-identity


And:

bash
aws s3 ls s3://your-bucket-name/


These commands require the AWS CLI and an appropriately configured identity.

13.4 Validate Pinecone Configuration

Ensure that:

The API key is valid.
The index exists.
The host is the full index URL.
The dimension is correct.
The similarity metric matches the index configuration.
The index supports the classic vectors API.
14. Index Provisioning
14.1 Create Pinecone Index

The project provides:

text
scripts/create_pinecone_index.py


Execute:

bash
python scripts/create_pinecone_index.py


The script provisions the Pinecone index.

The intended configuration is:

Setting	Value
Index type	Classic dense vectors
Dimension	1024
Metric	Cosine
Deployment	Serverless
Region	Configured Pinecone region
14.2 Configure Index Host

After index creation, copy the full host URL printed by the script.

Update:

env
PINECONE_INDEX_HOST="https://your-index-host.svc.ap-southeast-1.aws.pinecone.io"


Important: Recreating an index may change its host. Always update the environment configuration after recreating the index.

14.3 Classic Vector API Requirement

The application generates embeddings client-side through the embedding provider abstraction.

Therefore, the Pinecone index must support direct vector upserts and queries.

An index configured through Pinecone's integrated-embedding/document-schema workflow is not compatible with the application's current classic vectors API approach.

15. Testing and Validation
15.1 Smoke Test

The project includes:

text
scripts/smoke_vector_and_s3.py


Execute:

bash
python scripts/smoke_vector_and_s3.py


The script validates the integration between the application and the external infrastructure services.

15.2 S3 Validation

The test verifies:

Object upload.
Object storage URI generation.
Presigned URL generation.
Object cleanup.

Expected output:

text
S3 OK: s3://<bucket>/smoke/test-<ts>.txt

Presigned:
https://<bucket>.s3.amazonaws.com/smoke/test-<ts>.txt ...

S3 cleaned up

15.3 Pinecone Validation

The test verifies:

Connection to the index.
Index statistics retrieval.
Vector upsert.
Similarity query.
Vector cleanup.

Expected output:

text
Vector store stats:
{
    'dimension': 1024,
    'metric': 'cosine',
    'total_vector_count': 0
}

Query hits:
[('smoke-0001', ~1.0)]

Pinecone cleaned up


The exact statistics and vector counts may differ depending on the index's existing data.

15.4 Similarity Score Validation

A vector queried against itself should produce a cosine similarity close to:

text
1.0


This is a useful sanity check for vector upsert and retrieval.

It does not independently prove that the embedding model, document chunking, or end-to-end semantic retrieval is functioning correctly.

15.5 Test Coverage Recommendations
Test	Type	Purpose
Interface contract tests	Unit	Validate adapter behavior
Factory tests	Unit	Validate provider selection
Configuration tests	Unit	Validate settings
S3 upload/download	Integration	Validate object operations
S3 presigned URL	Integration	Validate URL generation
Pinecone upsert	Integration	Validate vector writes
Pinecone query	Integration	Validate retrieval
Pinecone delete	Integration	Validate cleanup
Cache reset	Unit/Integration	Validate dependency isolation
16. Error Handling and Exception Management

Location:

text
src/app/core/exceptions.py


The infrastructure extension introduces:

text
StorageError
StorageProviderError

16.1 StorageError

Represents storage-related operation failures.

Examples include:

Object not found.
Upload failure.
Download failure.
Delete failure.
Presigned URL generation failure.
16.2 StorageProviderError

Represents storage provider construction or initialization failures.

Examples include:

Missing bucket configuration.
Invalid provider selection.
Client initialization failure.
Invalid provider credentials.
16.3 Error Propagation
mermaid
flowchart TD
    A["Application Service"]
    B["Infrastructure Adapter"]
    C["External Provider"]

    A --> B
    B --> C

    C -->|Failure| D["Provider Exception"]
    D --> E["Adapter Error Handling"]
    E --> F["Application-Level Exception"]
    F --> G["Application Error Handling"]


Adapters should translate provider-specific exceptions into application-level exceptions where appropriate.

Original exceptions should be preserved as causes when possible to support debugging.

The exact exception mapping must follow the existing implementation.

17. Troubleshooting Guide

This section documents issues encountered during implementation and their corresponding resolutions.

Issue 1: BaseStorage NameError

Error:

text
NameError: name 'BaseStorage' is not defined


Cause:

The S3 adapter was missing the import for its interface.

Resolution:

Add:

python
from app.domains.interfaces.storage import BaseStorage


Explanation:

All infrastructure adapters must import and implement their corresponding application ports.

Ports are located under:

text
src/app/domains/interfaces/

Issue 2: Invalid Pinecone Host URL

Error:

text
host 'rag-knowledge-base'
does not appear to be a valid URL


Cause:

The configured value contained the index name rather than the full index host URL.

Resolution:

Use the complete URL from the Pinecone console:

env
PINECONE_INDEX_HOST="https://your-index-host.svc.ap-southeast-1.aws.pinecone.io"


Additional Consideration:

Shell-exported environment variables can override values from .env when using Pydantic Settings.

Check:

bash
echo "$PINECONE_INDEX_HOST"


If an incorrect value is exported:

bash
unset PINECONE_INDEX_HOST


Then restart the application or test process.

Issue 3: Pinecone Document Schema Error

Error:

text
[400] This index has a document schema,
so writes must go through the documents API


Cause:

The index was created using Pinecone's integrated-embedding workflow.

That index configuration expects writes through its Documents API rather than the classic vectors API used by this application.

Resolution:

Delete the incompatible index if it contains no data that must be retained.
Recreate the index using the project script.
Ensure that it is a classic dense-vector index.
Configure dimension 1024.
Configure cosine similarity.
Configure the intended serverless region.
Copy the new host into .env.

Execute:

bash
python scripts/create_pinecone_index.py


Architecture Explanation:

The application generates embeddings externally through:

text
BaseEmbeddings
    |
    v
Vercel AI Gateway
    |
    v
cohere/embed-v4.0
    |
    v
1024-dimensional vector
    |
    v
Pinecone classic vectors API


This keeps embedding generation within the application architecture and avoids coupling the system to Pinecone's integrated-embedding workflow.

Issue 4: Region Mismatch

Symptoms:

Connection errors or infrastructure access failures.

Cause:

The configured region does not match the actual resource region.

Resolution:

Verify:

env
PINECONE_REGION="ap-southeast-1"
AWS_REGION="ap-south-1"


The Pinecone region must match the provisioned index.

The AWS region must match the S3 bucket.

These services do not need to use the same region.

Issue 5: AWS Credentials Not Found

Possible Cause:

The application cannot resolve a valid AWS identity.

Resolution:

Verify the configured credentials or workload identity.

Run:

bash
aws sts get-caller-identity


Then validate bucket access:

bash
aws s3 ls s3://your-bucket-name/


Also verify that the application's runtime environment has access to the same identity.

Issue 6: Pinecone Dimension Mismatch

Possible Cause:

The embedding output dimension differs from the index dimension.

Resolution:

Verify:

env
PINECONE_DIMENSION=1024


Ensure the embedding model returns vectors with exactly the same dimension.

Do not change the index dimension without considering the embedding model and existing indexed vectors.

Issue 7: Stale Cached Provider

Possible Cause:

The dependency injection layer continues returning an earlier cached provider instance after configuration changes.

Resolution:

Use:

python
reset_all_caches()


Where appropriate, clear provider caches between provider-dependent test cases.

18. Security and Production Considerations
18.1 Credential Management

Never hardcode credentials inside:

Python source files.
Configuration classes.
Test fixtures.
Documentation containing real secrets.

Use environment variables or an appropriate secrets-management system.

18.2 IAM Permissions

The application should receive only the S3 permissions it needs.

Typical permissions include:

Permission	Purpose
s3:PutObject	Upload objects
s3:GetObject	Download objects
s3:DeleteObject	Delete objects
s3:ListBucket	List bucket objects, if required

Avoid granting unnecessary administrative permissions.

18.3 Presigned URL Security

Presigned URLs provide temporary access to S3 objects.

Recommended practices:

Use short expiration periods where practical.
Avoid logging complete presigned URLs.
Do not expose URLs unnecessarily.
Use private buckets by default.
Validate authorization before generating URLs.
18.4 Document Isolation

Document-level metadata filters should be used to restrict retrieval.

For multi-tenant applications, tenant identity must be enforced consistently in:

Upload authorization.
Vector metadata.
Namespace selection.
Retrieval filters.
Delete operations.

A client-provided filter alone must not be treated as an authorization boundary.

18.5 Data Lifecycle

The application should eventually define coordinated deletion policies.

For example, deleting a document may require:

Removing its Pinecone vectors.
Deleting its S3 original file.
Updating or deleting its PostgreSQL record.
Cleaning up related metadata.

The deletion workflow should account for partial failures and retry behavior.

19. Performance and Scalability
19.1 Vector Upsert Performance

The current Pinecone adapter uses batches of 100 vectors.

This provides a controlled write pattern for the current embedding dimension and metadata structure.

Future optimization can evaluate:

Batch sizing.
Concurrent batch submission.
Retry with backoff.
Rate-limit handling.
Throughput monitoring.
19.2 Object Storage Scalability

S3 provides managed object storage without requiring the application to manage storage servers.

For larger documents, future improvements may include:

Streaming uploads.
Multipart uploads.
Direct-to-S3 uploads using presigned URLs.
Object lifecycle policies.
Versioning where required.
19.3 Retrieval Optimization

Future retrieval improvements may include:

Metadata pre-filtering.
Configurable top-k.
Reranking.
Context deduplication.
Hybrid search.
Query caching.

These are potential optimizations and are not represented as currently implemented features.

19.4 Observability

Production deployments should monitor:

Metric	Purpose
S3 upload latency	Storage performance
S3 download latency	Retrieval performance
S3 operation failures	Storage reliability
Pinecone upsert latency	Indexing performance
Pinecone query latency	Retrieval performance
Vector count	Index growth
Embedding latency	Ingestion performance
Failed ingestion count	Pipeline reliability
Presigned URL generation failures	Storage access reliability

Logs should include useful correlation identifiers such as document IDs and request IDs without exposing credentials or sensitive document contents.

20. Implementation Roadmap

The current extension establishes the infrastructure foundation.

The following milestones describe the logical next development stages.

Milestone 1: Document Ingestion Service

Objective: Implement the complete document ingestion pipeline.

Tasks:

Create ingestion application service.
Integrate S3 document uploads.
Implement document text extraction.
Implement chunking using CHUNK_SIZE.
Implement overlap using CHUNK_OVERLAP.
Generate embeddings using BaseEmbeddings.
Upsert vectors into Pinecone.
Persist document metadata in PostgreSQL.
Update document status to ready.
Add failure handling and retry strategy.

Acceptance Criteria:

A supported document can be uploaded, stored, processed, embedded, indexed, and marked ready only after successful completion of the required operations.

Milestone 2: Retrieval Service

Objective: Implement semantic document retrieval.

Tasks:

Create retrieval application service.
Implement query embedding generation.
Integrate Pinecone similarity search.
Implement configurable top-k.
Add document metadata filters.
Construct LLM context from retrieved chunks.
Integrate optional reranking.
Add retrieval integration tests.

Acceptance Criteria:

A user query can retrieve relevant indexed document chunks and pass the resulting context to the LLM.

Milestone 3: Reliability and Production Readiness

Objective: Improve operational reliability.

Tasks:

Add structured infrastructure logging.
Implement provider retry policies.
Add timeout configuration.
Add ingestion failure recovery.
Implement coordinated document deletion.
Add integration test fixtures.
Validate IAM permissions.
Review tenant isolation.
Add monitoring and metrics.
Milestone 4: Infrastructure Extensibility

Objective: Expand the provider ecosystem without changing application contracts.

Potential extensions:

Qdrant vector store adapter.
Weaviate vector store adapter.
Azure Blob Storage adapter.
Google Cloud Storage adapter.
Additional provider-specific integration tests.

These extensions should continue implementing the existing ports.

21. Architecture Decisions

This section records the main architectural choices made during implementation.

Decision	Reason
Vendor-neutral vector interface	Prevent direct application coupling to Pinecone
Vendor-neutral storage interface	Support alternative object-storage providers
Pinecone classic vectors API	Use application-generated embeddings
Client-side embeddings	Maintain independent embedding-provider abstraction
AWS S3 adapter	Provide durable managed object storage
Factory-based provider creation	Centralize provider construction
Dependency injection	Separate composition from business logic
Cached provider dependencies	Reuse infrastructure clients
Environment-based configuration	Separate deployment configuration from source code
Pinecone batching	Control vector write request sizes
Presigned S3 URLs	Enable temporary object access without public bucket exposure
21.1 Important Design Constraint

The vector database is responsible for storing and searching embeddings.

The object storage service is responsible for storing original files.

These responsibilities must remain separate.

mermaid
flowchart LR
    A["Original Document"] --> B["AWS S3"]
    A --> C["Text Extraction"]
    C --> D["Chunking"]
    D --> E["Embedding Model"]
    E --> F["Pinecone"]

    B --> G["Original File Storage"]
    F --> H["Semantic Retrieval"]


S3 is not a replacement for Pinecone, and Pinecone is not a replacement for S3.

Both services contribute different capabilities to the overall RAG architecture.

22. Conclusion

This infrastructure extension establishes a reusable foundation for vector storage and object storage within the application's existing Hexagonal Architecture.

The implementation introduces:

A vendor-neutral vector database contract.
A Pinecone Serverless adapter.
A vendor-neutral object storage contract.
An AWS S3 adapter.
Independent provider factories.
Centralized dependency injection.
Environment-driven infrastructure configuration.
Index provisioning and integration smoke tests.
A documented foundation for future RAG ingestion and retrieval services.

The separation between application interfaces and infrastructure implementations ensures that future provider changes can be introduced without unnecessarily modifying application business logic.

Current milestone: Infrastructure interfaces, Pinecone integration, S3 integration, factories, configuration, and smoke testing.

Next milestone: End-to-end document ingestion and semantic retrieval.

Quick Reference
Install Dependencies
bash
pip install pinecone boto3

Create Pinecone Index
bash
python scripts/create_pinecone_index.py

Run Infrastructure Smoke Test
bash
python scripts/smoke_vector_and_s3.py

Important Configuration
env
VECTOR_STORE_PROVIDER="pinecone"
PINECONE_DIMENSION=1024

STORAGE_PROVIDER="aws"
S3_PRESIGN_EXPIRY=3600

Core Interfaces
text
BaseVectorStore
BaseStorage

Core Implementations
text
PineconeVectorStore
S3Storage

Dependency Injection
python
get_vector_store()
get_storage()

Core Infrastructure
text
Pinecone Serverless
Amazon S3


Document: Vector Store (Pinecone) & Object Storage (AWS S3)
Project: Project 4 — Infrastructure Layer Extension
Architecture: Hexagonal Architecture (Ports & Adapters)
Documentation Type: Technical Architecture and Implementation Guide