package org.booklore.service.department;

import lombok.RequiredArgsConstructor;
import org.booklore.config.security.service.AuthenticationService;
import org.booklore.exception.ApiError;
import org.booklore.model.dto.BookLoreUser;
import org.booklore.model.dto.DepartmentDto;
import org.booklore.model.dto.request.AddDepartmentMemberRequest;
import org.booklore.model.dto.request.CreateDepartmentRequest;
import org.booklore.model.entity.BookLoreUserEntity;
import org.booklore.model.entity.DepartmentEntity;
import org.booklore.model.entity.DepartmentMemberEntity;
import org.booklore.model.enums.DepartmentRole;
import org.booklore.repository.DepartmentMemberRepository;
import org.booklore.repository.DepartmentRepository;
import org.booklore.repository.UserRepository;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.util.ArrayList;
import java.util.List;
import java.util.stream.Collectors;

@Service
@RequiredArgsConstructor
public class DepartmentService {

    private final DepartmentRepository departmentRepository;
    private final DepartmentMemberRepository departmentMemberRepository;
    private final UserRepository userRepository;
    private final AuthenticationService authenticationService;

    // ─── Yaratish ─────────────────────────────────────────────────────────────

    @Transactional
    public DepartmentDto createDepartment(CreateDepartmentRequest request) {
        BookLoreUser currentUser = authenticationService.getAuthenticatedUser();

        DepartmentEntity parent = null;
        if (request.getParentId() != null) {
            parent = departmentRepository.findById(request.getParentId())
                    .orElseThrow(() -> ApiError.DEPARTMENT_NOT_FOUND.createException(request.getParentId()));

            // Admin yoki parent bo'limning boshliqgina child qo'sha oladi
            if (!currentUser.getPermissions().isAdmin()) {
                boolean isHeadOfParent = departmentMemberRepository
                        .existsByDepartmentIdAndUserIdAndRole(parent.getId(), currentUser.getId(), DepartmentRole.HEAD);
                if (!isHeadOfParent) {
                    throw ApiError.DEPARTMENT_ACCESS_DENIED.createException();
                }
            }
        } else {
            // Root bo'lim faqat admin yarata oladi
            if (!currentUser.getPermissions().isAdmin()) {
                throw ApiError.DEPARTMENT_ACCESS_DENIED.createException();
            }
        }

        DepartmentEntity department = DepartmentEntity.builder()
                .name(request.getName())
                .description(request.getDescription())
                .parent(parent)
                .build();

        department = departmentRepository.save(department);

        // Boshliq tayinlash
        if (request.getHeadUserId() != null) {
            addMemberInternal(department, request.getHeadUserId(), DepartmentRole.HEAD);
        }

        return toDto(department, true);
    }

    // ─── O'qish ───────────────────────────────────────────────────────────────

    /**
     * Foydalanuvchi ko'ra oladigan bo'limlarni qaytaradi.
     * Admin — barchani ko'radi (faqat root darajadan).
     * Oddiy foydalanuvchi — faqat o'zi boshliq bo'lgan bo'limlarning subtree'ini ko'radi.
     */
    public List<DepartmentDto> getAccessibleDepartments() {
        BookLoreUser currentUser = authenticationService.getAuthenticatedUser();

        if (currentUser.getPermissions().isAdmin()) {
            return departmentRepository.findByParentIsNull()
                    .stream()
                    .map(d -> toDto(d, true))
                    .collect(Collectors.toList());
        }

        // Foydalanuvchi boshliq bo'lgan bo'limlarning subtree'ini qaytarish
        List<DepartmentEntity> headDepartments = departmentRepository
                .findDepartmentsWhereUserIsHead(currentUser.getId());

        return headDepartments.stream()
                .map(d -> toDto(d, true))
                .collect(Collectors.toList());
    }

    public DepartmentDto getDepartmentById(Long id) {
        BookLoreUser currentUser = authenticationService.getAuthenticatedUser();
        DepartmentEntity department = departmentRepository.findById(id)
                .orElseThrow(() -> ApiError.DEPARTMENT_NOT_FOUND.createException(id));

        if (!currentUser.getPermissions().isAdmin() && !isAccessible(department, currentUser.getId())) {
            throw ApiError.DEPARTMENT_ACCESS_DENIED.createException();
        }

        return toDto(department, true);
    }

    // ─── Yangilash ────────────────────────────────────────────────────────────

    @Transactional
    public DepartmentDto updateDepartment(Long id, CreateDepartmentRequest request) {
        BookLoreUser currentUser = authenticationService.getAuthenticatedUser();
        DepartmentEntity department = departmentRepository.findById(id)
                .orElseThrow(() -> ApiError.DEPARTMENT_NOT_FOUND.createException(id));

        if (!currentUser.getPermissions().isAdmin() && !isHeadOf(department, currentUser.getId())) {
            throw ApiError.DEPARTMENT_ACCESS_DENIED.createException();
        }

        department.setName(request.getName());
        department.setDescription(request.getDescription());

        // Parent o'zgartirishga faqat admin ruxsat
        if (request.getParentId() != null && currentUser.getPermissions().isAdmin()) {
            if (isAncestorOf(department.getId(), request.getParentId())) {
                throw ApiError.DEPARTMENT_CIRCULAR_REFERENCE.createException();
            }
            DepartmentEntity newParent = departmentRepository.findById(request.getParentId())
                    .orElseThrow(() -> ApiError.DEPARTMENT_NOT_FOUND.createException(request.getParentId()));
            department.setParent(newParent);
        }

        return toDto(departmentRepository.save(department), true);
    }

    // ─── O'chirish ────────────────────────────────────────────────────────────

    @Transactional
    public void deleteDepartment(Long id) {
        BookLoreUser currentUser = authenticationService.getAuthenticatedUser();
        if (!currentUser.getPermissions().isAdmin()) {
            throw ApiError.DEPARTMENT_ACCESS_DENIED.createException();
        }
        DepartmentEntity department = departmentRepository.findById(id)
                .orElseThrow(() -> ApiError.DEPARTMENT_NOT_FOUND.createException(id));
        departmentRepository.delete(department);
    }

    // ─── A'zolar ──────────────────────────────────────────────────────────────

    @Transactional
    public DepartmentDto addMember(Long departmentId, AddDepartmentMemberRequest request) {
        BookLoreUser currentUser = authenticationService.getAuthenticatedUser();
        DepartmentEntity department = departmentRepository.findById(departmentId)
                .orElseThrow(() -> ApiError.DEPARTMENT_NOT_FOUND.createException(departmentId));

        // Admin yoki shu bo'limning boshliqgina a'zo qo'sha oladi
        if (!currentUser.getPermissions().isAdmin() && !isHeadOf(department, currentUser.getId())) {
            throw ApiError.DEPARTMENT_ACCESS_DENIED.createException();
        }

        if (departmentMemberRepository.existsByDepartmentIdAndUserId(departmentId, request.getUserId())) {
            throw ApiError.DEPARTMENT_MEMBER_ALREADY_EXISTS.createException();
        }

        DepartmentRole role = request.getRole() != null ? request.getRole() : DepartmentRole.MEMBER;
        addMemberInternal(department, request.getUserId(), role);

        return toDto(department, true);
    }

    @Transactional
    public void removeMember(Long departmentId, Long userId) {
        BookLoreUser currentUser = authenticationService.getAuthenticatedUser();
        DepartmentEntity department = departmentRepository.findById(departmentId)
                .orElseThrow(() -> ApiError.DEPARTMENT_NOT_FOUND.createException(departmentId));

        if (!currentUser.getPermissions().isAdmin() && !isHeadOf(department, currentUser.getId())) {
            throw ApiError.DEPARTMENT_ACCESS_DENIED.createException();
        }

        if (!departmentMemberRepository.existsByDepartmentIdAndUserId(departmentId, userId)) {
            throw ApiError.DEPARTMENT_MEMBER_NOT_FOUND.createException();
        }

        departmentMemberRepository.deleteByDepartmentIdAndUserId(departmentId, userId);
    }

    @Transactional
    public DepartmentDto setMemberRole(Long departmentId, Long userId, DepartmentRole role) {
        BookLoreUser currentUser = authenticationService.getAuthenticatedUser();
        DepartmentEntity department = departmentRepository.findById(departmentId)
                .orElseThrow(() -> ApiError.DEPARTMENT_NOT_FOUND.createException(departmentId));

        if (!currentUser.getPermissions().isAdmin() && !isHeadOf(department, currentUser.getId())) {
            throw ApiError.DEPARTMENT_ACCESS_DENIED.createException();
        }

        DepartmentMemberEntity member = departmentMemberRepository
                .findByDepartmentIdAndUserId(departmentId, userId)
                .orElseThrow(() -> ApiError.DEPARTMENT_MEMBER_NOT_FOUND.createException());

        member.setRole(role);
        departmentMemberRepository.save(member);

        return toDto(department, true);
    }

    public List<DepartmentDto.MemberDto> getDepartmentMembers(Long departmentId) {
        BookLoreUser currentUser = authenticationService.getAuthenticatedUser();
        DepartmentEntity department = departmentRepository.findById(departmentId)
                .orElseThrow(() -> ApiError.DEPARTMENT_NOT_FOUND.createException(departmentId));

        if (!currentUser.getPermissions().isAdmin() && !isAccessible(department, currentUser.getId())) {
            throw ApiError.DEPARTMENT_ACCESS_DENIED.createException();
        }

        return departmentMemberRepository.findByDepartmentId(departmentId)
                .stream()
                .map(this::toMemberDto)
                .collect(Collectors.toList());
    }

    // ─── Yordamchi metodlar ───────────────────────────────────────────────────

    private void addMemberInternal(DepartmentEntity department, Long userId, DepartmentRole role) {
        BookLoreUserEntity user = userRepository.findById(userId)
                .orElseThrow(() -> ApiError.USER_NOT_FOUND.createException(userId));

        DepartmentMemberEntity member = DepartmentMemberEntity.builder()
                .department(department)
                .user(user)
                .role(role)
                .build();

        departmentMemberRepository.save(member);
    }

    /**
     * Foydalanuvchi ushbu bo'lim yoki uning biror ajdodi (ancestor)ning boshlig'i ekanligini tekshiradi.
     * Shu bilan boshlig' o'zining barcha child bo'limlarini ko'ra oladi.
     */
    boolean isAccessible(DepartmentEntity department, Long userId) {
        if (isHeadOf(department, userId)) return true;
        if (department.getParent() == null) return false;
        return isAccessible(department.getParent(), userId);
    }

    private boolean isHeadOf(DepartmentEntity department, Long userId) {
        return departmentMemberRepository.existsByDepartmentIdAndUserIdAndRole(
                department.getId(), userId, DepartmentRole.HEAD);
    }

    /**
     * Circular reference tekshiruvi: potentialAncestorId, childId ning ajdodi ekanligini tekshiradi.
     */
    private boolean isAncestorOf(Long childId, Long potentialAncestorId) {
        if (childId.equals(potentialAncestorId)) return true;
        DepartmentEntity child = departmentRepository.findById(childId).orElse(null);
        if (child == null || child.getParent() == null) return false;
        return isAncestorOf(child.getParent().getId(), potentialAncestorId);
    }

    // ─── DTO o'zgartirgichlar ─────────────────────────────────────────────────

    private DepartmentDto toDto(DepartmentEntity entity, boolean includeChildren) {
        List<DepartmentDto> childDtos = new ArrayList<>();
        if (includeChildren && entity.getChildren() != null) {
            childDtos = entity.getChildren().stream()
                    .map(child -> toDto(child, true))
                    .collect(Collectors.toList());
        }

        List<DepartmentDto.MemberDto> memberDtos = new ArrayList<>();
        if (entity.getMembers() != null) {
            memberDtos = entity.getMembers().stream()
                    .map(this::toMemberDto)
                    .collect(Collectors.toList());
        }

        return DepartmentDto.builder()
                .id(entity.getId())
                .name(entity.getName())
                .description(entity.getDescription())
                .parentId(entity.getParent() != null ? entity.getParent().getId() : null)
                .parentName(entity.getParent() != null ? entity.getParent().getName() : null)
                .createdAt(entity.getCreatedAt())
                .children(childDtos)
                .members(memberDtos)
                .build();
    }

    private DepartmentDto.MemberDto toMemberDto(DepartmentMemberEntity member) {
        return DepartmentDto.MemberDto.builder()
                .userId(member.getUser().getId())
                .username(member.getUser().getUsername())
                .name(member.getUser().getName())
                .email(member.getUser().getEmail())
                .role(member.getRole())
                .joinedAt(member.getJoinedAt())
                .build();
    }
}
