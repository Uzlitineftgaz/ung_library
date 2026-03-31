ALTER TABLE library ADD COLUMN parent_id BIGINT NULL;

ALTER TABLE library
    ADD CONSTRAINT fk_library_parent
        FOREIGN KEY (parent_id) REFERENCES library(id) ON DELETE SET NULL;
