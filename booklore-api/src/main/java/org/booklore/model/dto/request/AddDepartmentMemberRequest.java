package org.booklore.model.dto.request;

import jakarta.validation.constraints.NotNull;
import lombok.Data;
import org.booklore.model.enums.DepartmentRole;

@Data
public class AddDepartmentMemberRequest {

    @NotNull(message = "User ID is required")
    private Long userId;

    private DepartmentRole role = DepartmentRole.MEMBER;
}
