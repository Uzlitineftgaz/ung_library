package org.booklore.repository;

import org.booklore.model.entity.DepartmentMemberEntity;
import org.booklore.model.enums.DepartmentRole;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.stereotype.Repository;

import java.util.List;
import java.util.Optional;

@Repository
public interface DepartmentMemberRepository extends JpaRepository<DepartmentMemberEntity, Long> {

    Optional<DepartmentMemberEntity> findByDepartmentIdAndUserId(Long departmentId, Long userId);

    List<DepartmentMemberEntity> findByDepartmentId(Long departmentId);

    boolean existsByDepartmentIdAndUserIdAndRole(Long departmentId, Long userId, DepartmentRole role);

    boolean existsByDepartmentIdAndUserId(Long departmentId, Long userId);

    void deleteByDepartmentIdAndUserId(Long departmentId, Long userId);
}
