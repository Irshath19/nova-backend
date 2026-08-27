-- 1. Enable pgvector extension
CREATE EXTENSION IF NOT EXISTS vector;

-- 2. Drop existing tables if re-creating
DROP TABLE IF EXISTS learning_path_items CASCADE;
DROP TABLE IF EXISTS learning_paths CASCADE;
DROP TABLE IF EXISTS note_concepts CASCADE;
DROP TABLE IF EXISTS note_tags CASCADE;
DROP TABLE IF EXISTS notes CASCADE;
DROP TABLE IF EXISTS concept_relationships CASCADE;
DROP TABLE IF EXISTS concepts CASCADE;
DROP TABLE IF EXISTS tags CASCADE;
DROP TABLE IF EXISTS users CASCADE;

DROP TYPE IF EXISTS knowledge_level_enum CASCADE;
DROP TYPE IF EXISTS relationship_type_enum CASCADE;
DROP TYPE IF EXISTS processing_status_enum CASCADE;
DROP TYPE IF EXISTS path_item_status_enum CASCADE;

-- 3. ENUM Types
CREATE TYPE knowledge_level_enum AS ENUM (
    'NEW',
    'FAMILIAR',
    'LEARNING',
    'INTERMEDIATE',
    'STRONG'
);

CREATE TYPE relationship_type_enum AS ENUM (
    'USES',
    'DEPENDS_ON',
    'PART_OF',
    'RELATED_TO',
    'LEADS_TO'
);

CREATE TYPE processing_status_enum AS ENUM (
    'PENDING',
    'PROCESSING',
    'COMPLETED',
    'FAILED'
);

CREATE TYPE path_item_status_enum AS ENUM (
    'NOT_STARTED',
    'IN_PROGRESS',
    'COMPLETED'
);

-- 4. Users Table
CREATE TABLE users (
    id VARCHAR(36) PRIMARY KEY,
    email VARCHAR(255) UNIQUE NOT NULL,
    username VARCHAR(100) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- 5. Tags Table
CREATE TABLE tags (
    id VARCHAR(36) PRIMARY KEY,
    user_id VARCHAR(36) NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    name VARCHAR(100) NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_user_tag_name UNIQUE (user_id, name)
);

CREATE INDEX idx_tags_user ON tags(user_id);
CREATE INDEX idx_tags_name ON tags(name);

-- 6. Concepts Table (with 768-dim Vector Embeddings)
CREATE TABLE concepts (
    id VARCHAR(36) PRIMARY KEY,
    user_id VARCHAR(36) NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    name VARCHAR(150) NOT NULL,
    description TEXT,
    knowledge_level knowledge_level_enum NOT NULL DEFAULT 'NEW',
    embedding VECTOR(768),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_user_concept_name UNIQUE (user_id, name)
);

CREATE INDEX idx_concepts_user ON concepts(user_id);
CREATE INDEX idx_concepts_name ON concepts(name);

-- 7. Concept Relationships (Knowledge Graph Edges)
CREATE TABLE concept_relationships (
    id VARCHAR(36) PRIMARY KEY,
    user_id VARCHAR(36) NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    source_concept_id VARCHAR(36) NOT NULL REFERENCES concepts(id) ON DELETE CASCADE,
    target_concept_id VARCHAR(36) NOT NULL REFERENCES concepts(id) ON DELETE CASCADE,
    relationship_type relationship_type_enum NOT NULL DEFAULT 'RELATED_TO',
    weight FLOAT NOT NULL DEFAULT 1.0,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_user_source_target_rel UNIQUE (user_id, source_concept_id, target_concept_id, relationship_type)
);

CREATE INDEX idx_rel_user ON concept_relationships(user_id);
CREATE INDEX idx_rel_source ON concept_relationships(source_concept_id);
CREATE INDEX idx_rel_target ON concept_relationships(target_concept_id);

-- 8. Notes Table (with 768-dim Vector Embeddings)
CREATE TABLE notes (
    id VARCHAR(36) PRIMARY KEY,
    user_id VARCHAR(36) NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    title VARCHAR(255) NOT NULL,
    content TEXT NOT NULL,
    summary TEXT,
    source VARCHAR(500),
    embedding VECTOR(768),
    processing_status processing_status_enum NOT NULL DEFAULT 'PENDING',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_notes_user ON notes(user_id);
CREATE INDEX idx_notes_title ON notes(title);

-- 9. Note Tags Junction Table
CREATE TABLE note_tags (
    note_id VARCHAR(36) NOT NULL REFERENCES notes(id) ON DELETE CASCADE,
    tag_id VARCHAR(36) NOT NULL REFERENCES tags(id) ON DELETE CASCADE,
    PRIMARY KEY (note_id, tag_id)
);

-- 10. Note Concepts Junction Table
CREATE TABLE note_concepts (
    note_id VARCHAR(36) NOT NULL REFERENCES notes(id) ON DELETE CASCADE,
    concept_id VARCHAR(36) NOT NULL REFERENCES concepts(id) ON DELETE CASCADE,
    PRIMARY KEY (note_id, concept_id)
);

-- 11. Learning Paths Table
CREATE TABLE learning_paths (
    id VARCHAR(36) PRIMARY KEY,
    user_id VARCHAR(36) NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    title VARCHAR(255) NOT NULL,
    description TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_lp_user ON learning_paths(user_id);

-- 12. Learning Path Items (Roadmap Steps)
CREATE TABLE learning_path_items (
    id VARCHAR(36) PRIMARY KEY,
    learning_path_id VARCHAR(36) NOT NULL REFERENCES learning_paths(id) ON DELETE CASCADE,
    concept_id VARCHAR(36) NOT NULL REFERENCES concepts(id) ON DELETE CASCADE,
    position INTEGER NOT NULL DEFAULT 0,
    status path_item_status_enum NOT NULL DEFAULT 'NOT_STARTED'
);

CREATE INDEX idx_lpi_path ON learning_path_items(learning_path_id);
CREATE INDEX idx_lpi_concept ON learning_path_items(concept_id);
