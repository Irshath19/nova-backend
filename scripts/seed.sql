-- 1. Insert Demo User (Password is 'nova123456' hashed with bcrypt)
INSERT INTO users (id, email, username, password_hash)
VALUES (
    '0d8c6167-a32c-4cc1-97f5-1c952a756736',
    'demo@nova.ai',
    'nova_explorer',
    '$2b$12$K8yR2u2h5i63k1T4tJzIbeO.oGhy7b6.5L34k05sX/Q2N1w.9y2eW'
) ON CONFLICT (id) DO NOTHING;

-- 2. Insert Tags
INSERT INTO tags (id, user_id, name) VALUES
('t-01', '0d8c6167-a32c-4cc1-97f5-1c952a756736', 'ai'),
('t-02', '0d8c6167-a32c-4cc1-97f5-1c952a756736', 'llm'),
('t-03', '0d8c6167-a32c-4cc1-97f5-1c952a756736', 'rag'),
('t-04', '0d8c6167-a32c-4cc1-97f5-1c952a756736', 'agents'),
('t-05', '0d8c6167-a32c-4cc1-97f5-1c952a756736', 'embeddings'),
('t-06', '0d8c6167-a32c-4cc1-97f5-1c952a756736', 'system-design');

-- 3. Insert Concepts with Knowledge Levels
INSERT INTO concepts (id, user_id, name, description, knowledge_level) VALUES
('c-01', '0d8c6167-a32c-4cc1-97f5-1c952a756736', 'Large Language Models', 'Transformer-based generative neural networks capable of natural language processing and complex reasoning.', 'STRONG'),
('c-02', '0d8c6167-a32c-4cc1-97f5-1c952a756736', 'Vector Embeddings', 'High-dimensional vector representations capturing semantic relationships between text chunks.', 'STRONG'),
('c-03', '0d8c6167-a32c-4cc1-97f5-1c952a756736', 'Retrieval-Augmented Generation', 'Technique that enhances LLM responses by retrieving relevant external context from vector databases.', 'INTERMEDIATE'),
('c-04', '0d8c6167-a32c-4cc1-97f5-1c952a756736', 'AI Agents', 'Autonomous software entities that use LLMs for reasoning, tool use, memory, and multi-step planning.', 'LEARNING'),
('c-05', '0d8c6167-a32c-4cc1-97f5-1c952a756736', 'Prompt Engineering', 'Techniques for crafting effective model instructions, few-shot examples, and chain-of-thought prompts.', 'FAMILIAR'),
('c-06', '0d8c6167-a32c-4cc1-97f5-1c952a756736', 'Hierarchical Navigable Small World (HNSW)', 'Graph-based approximate nearest neighbor search algorithm used in vector databases for sub-millisecond retrieval.', 'NEW'),
('c-07', '0d8c6167-a32c-4cc1-97f5-1c952a756736', 'ReAct Prompting', 'Synergizing reasoning and acting in language models to execute step-by-step tools.', 'LEARNING'),
('c-08', '0d8c6167-a32c-4cc1-97f5-1c952a756736', 'Vector Databases', 'Specialized data stores optimized for storing, indexing, and querying high-dimensional vector embeddings.', 'INTERMEDIATE'),
('c-09', '0d8c6167-a32c-4cc1-97f5-1c952a756736', 'Knowledge Graphs', 'Network structured knowledge representations connecting entities and semantic relations.', 'FAMILIAR'),
('c-10', '0d8c6167-a32c-4cc1-97f5-1c952a756736', 'Cosine Similarity', 'Metric calculating the cosine of the angle between two vectors to determine semantic similarity.', 'STRONG');

-- 4. Insert Graph Relationships (Edges)
INSERT INTO concept_relationships (id, user_id, source_concept_id, target_concept_id, relationship_type, weight) VALUES
('r-01', '0d8c6167-a32c-4cc1-97f5-1c952a756736', 'c-03', 'c-01', 'USES', 1.0),
('r-02', '0d8c6167-a32c-4cc1-97f5-1c952a756736', 'c-03', 'c-02', 'DEPENDS_ON', 1.0),
('r-03', '0d8c6167-a32c-4cc1-97f5-1c952a756736', 'c-04', 'c-01', 'USES', 1.0),
('r-04', '0d8c6167-a32c-4cc1-97f5-1c952a756736', 'c-04', 'c-03', 'USES', 1.0),
('r-05', '0d8c6167-a32c-4cc1-97f5-1c952a756736', 'c-02', 'c-06', 'RELATED_TO', 1.0),
('r-06', '0d8c6167-a32c-4cc1-97f5-1c952a756736', 'c-04', 'c-07', 'USES', 1.0),
('r-07', '0d8c6167-a32c-4cc1-97f5-1c952a756736', 'c-08', 'c-02', 'DEPENDS_ON', 1.0),
('r-08', '0d8c6167-a32c-4cc1-97f5-1c952a756736', 'c-08', 'c-06', 'USES', 1.0),
('r-09', '0d8c6167-a32c-4cc1-97f5-1c952a756736', 'c-02', 'c-10', 'RELATED_TO', 1.0),
('r-10', '0d8c6167-a32c-4cc1-97f5-1c952a756736', 'c-09', 'c-03', 'RELATED_TO', 1.0);

-- 5. Insert Sample Notes
INSERT INTO notes (id, user_id, title, content, summary, source, processing_status) VALUES
(
    'n-01',
    '0d8c6167-a32c-4cc1-97f5-1c952a756736',
    'Understanding RAG Architecture & Vector Indexing',
    '<p>Retrieval-Augmented Generation (RAG) combines dense vector search with large language models. The indexing pipeline breaks documents into chunks, generates vector embeddings, and stores them in PostgreSQL using pgvector with HNSW indexes.</p>',
    'RAG connects vector databases to LLM prompts for grounded factual generation.',
    'https://arxiv.org/abs/2005.11401',
    'COMPLETED'
),
(
    'n-02',
    '0d8c6167-a32c-4cc1-97f5-1c952a756736',
    'Building Autonomous AI Agents with Tool Calling',
    '<p>AI Agents require four foundational pillars: reasoning loop (ReAct), external tool execution, short/long-term memory, and multi-step planning to break down complex goals into tasks.</p>',
    'Autonomous agents leverage LLM reasoning, memory, tools, and planning.',
    'https://e2b.dev/blog',
    'COMPLETED'
),
(
    'n-03',
    '0d8c6167-a32c-4cc1-97f5-1c952a756736',
    'High Performance Vector Search with HNSW and pgvector',
    '<p>HNSW builds a multi-layer graph where bottom layers contain all data points and upper layers skip across long distances. In pgvector on PostgreSQL, creating an HNSW index with cosine distance operator <code>vector_cosine_ops</code> enables sub-10ms similarity searches across millions of documents.</p>',
    'HNSW provides sub-10ms approximate nearest neighbor search on vector databases.',
    'https://github.com/pgvector/pgvector',
    'COMPLETED'
),
(
    'n-04',
    '0d8c6167-a32c-4cc1-97f5-1c952a756736',
    'Effective Prompt Engineering Patterns for Production',
    '<p>System prompts should include explicit role definitions, strict output constraints (such as valid JSON schemas), few-shot examples of positive and negative cases, and step-by-step reasoning triggers to minimize hallucinations.</p>',
    'Production prompt engineering requires explicit constraints, JSON output schemas, and few-shot examples.',
    'https://docs.anthropic.com/en/docs/build-with-claude/prompt-engineering',
    'COMPLETED'
);

-- 6. Link Notes to Tags & Concepts
INSERT INTO note_tags (note_id, tag_id) VALUES
('n-01', 't-01'), ('n-01', 't-03'), ('n-01', 't-05'),
('n-02', 't-01'), ('n-02', 't-04'),
('n-03', 't-05'), ('n-03', 't-06'),
('n-04', 't-01'), ('n-04', 't-02');

INSERT INTO note_concepts (note_id, concept_id) VALUES
('n-01', 'c-01'), ('n-01', 'c-02'), ('n-01', 'c-03'), ('n-01', 'c-06'),
('n-02', 'c-01'), ('n-02', 'c-04'), ('n-02', 'c-07'),
('n-03', 'c-02'), ('n-03', 'c-06'), ('n-03', 'c-08'), ('n-03', 'c-10'),
('n-04', 'c-01'), ('n-04', 'c-05');

-- 7. Insert Learning Path
INSERT INTO learning_paths (id, user_id, title, description)
VALUES (
    'lp-01',
    '0d8c6167-a32c-4cc1-97f5-1c952a756736',
    'Full-Stack AI Engineer Roadmap',
    'From fundamental vector embeddings to advanced autonomous multi-agent architectures.'
);

-- 8. Insert Roadmap Step Items
INSERT INTO learning_path_items (id, learning_path_id, concept_id, position, status) VALUES
('lpi-01', 'lp-01', 'c-01', 0, 'COMPLETED'),
('lpi-02', 'lp-01', 'c-02', 1, 'COMPLETED'),
('lpi-03', 'lp-01', 'c-03', 2, 'IN_PROGRESS'),
('lpi-04', 'lp-01', 'c-04', 3, 'NOT_STARTED'),
('lpi-05', 'lp-01', 'c-07', 4, 'NOT_STARTED');
