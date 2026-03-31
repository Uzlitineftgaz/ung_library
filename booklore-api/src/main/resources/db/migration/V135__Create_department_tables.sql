-- Bo'limlar jadvali (ichma-ich ierarxiya bilan)
CREATE TABLE department
(
    id          BIGINT AUTO_INCREMENT PRIMARY KEY,
    name        VARCHAR(255) NOT NULL,
    description TEXT,
    parent_id   BIGINT       NULL,
    created_at  DATETIME     NOT NULL,
    CONSTRAINT fk_department_parent FOREIGN KEY (parent_id) REFERENCES department (id) ON DELETE CASCADE
);

-- Bo'lim a'zolari jadvali (HEAD yoki MEMBER roli bilan)
CREATE TABLE department_member
(
    id            BIGINT AUTO_INCREMENT PRIMARY KEY,
    department_id BIGINT      NOT NULL,
    user_id       BIGINT      NOT NULL,
    role          VARCHAR(20) NOT NULL DEFAULT 'MEMBER',
    joined_at     DATETIME    NOT NULL,
    CONSTRAINT fk_dept_member_department FOREIGN KEY (department_id) REFERENCES department (id) ON DELETE CASCADE,
    CONSTRAINT fk_dept_member_user FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE,
    CONSTRAINT uq_dept_member UNIQUE (department_id, user_id)
);

CREATE INDEX idx_department_parent ON department (parent_id);
CREATE INDEX idx_dept_member_user ON department_member (user_id);
CREATE INDEX idx_dept_member_dept ON department_member (department_id);
CREATE INDEX idx_dept_member_role ON department_member (department_id, role);
