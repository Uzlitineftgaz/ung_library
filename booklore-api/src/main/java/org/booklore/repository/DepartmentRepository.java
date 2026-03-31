package org.booklore.repository;

import org.booklore.model.entity.DepartmentEntity;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;
import org.springframework.stereotype.Repository;

import java.util.List;

@Repository
public interface DepartmentRepository extends JpaRepository<DepartmentEntity, Long> {

    List<DepartmentEntity> findByParentIsNull();

    List<DepartmentEntity> findByParentId(Long parentId);

    @Query("SELECT d FROM DepartmentEntity d JOIN d.members m WHERE m.user.id = :userId AND m.role = 'HEAD'")
    List<DepartmentEntity> findDepartmentsWhereUserIsHead(@Param("userId") Long userId);

    @Query("SELECT d FROM DepartmentEntity d JOIN d.members m WHERE m.user.id = :userId")
    List<DepartmentEntity> findDepartmentsForUser(@Param("userId") Long userId);
}
