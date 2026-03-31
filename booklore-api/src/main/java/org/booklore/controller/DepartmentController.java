package org.booklore.controller;

import io.swagger.v3.oas.annotations.Operation;
import io.swagger.v3.oas.annotations.Parameter;
import io.swagger.v3.oas.annotations.responses.ApiResponse;
import io.swagger.v3.oas.annotations.tags.Tag;
import jakarta.validation.Valid;
import lombok.AllArgsConstructor;
import org.booklore.model.dto.DepartmentDto;
import org.booklore.model.dto.request.AddDepartmentMemberRequest;
import org.booklore.model.dto.request.CreateDepartmentRequest;
import org.booklore.model.enums.DepartmentRole;
import org.booklore.service.department.DepartmentService;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

import java.util.List;

@AllArgsConstructor
@RestController
@RequestMapping("/api/v1/departments")
@Tag(name = "Departments", description = "Bo'limlarni boshqarish uchun endpointlar")
public class DepartmentController {

    private final DepartmentService departmentService;

    @Operation(summary = "Barcha bo'limlarni olish",
            description = "Admin barcha root bo'limlarni ko'radi. Bo'lim boshlig'i faqat o'z subtree'ini ko'radi.")
    @ApiResponse(responseCode = "200", description = "Bo'limlar ro'yxati qaytarildi")
    @GetMapping
    public ResponseEntity<List<DepartmentDto>> getDepartments() {
        return ResponseEntity.ok(departmentService.getAccessibleDepartments());
    }

    @Operation(summary = "Bo'limni ID bo'yicha olish")
    @ApiResponse(responseCode = "200", description = "Bo'lim qaytarildi")
    @ApiResponse(responseCode = "403", description = "Ruxsat yo'q")
    @ApiResponse(responseCode = "404", description = "Topilmadi")
    @GetMapping("/{id}")
    public ResponseEntity<DepartmentDto> getDepartment(
            @Parameter(description = "Bo'lim ID") @PathVariable Long id) {
        return ResponseEntity.ok(departmentService.getDepartmentById(id));
    }

    @Operation(summary = "Yangi bo'lim yaratish",
            description = "Root bo'lim faqat admin yarata oladi. Child bo'limni boshliq ham yarata oladi.")
    @ApiResponse(responseCode = "201", description = "Bo'lim yaratildi")
    @PostMapping
    public ResponseEntity<DepartmentDto> createDepartment(
            @Valid @RequestBody CreateDepartmentRequest request) {
        return ResponseEntity.status(HttpStatus.CREATED)
                .body(departmentService.createDepartment(request));
    }

    @Operation(summary = "Bo'limni yangilash")
    @ApiResponse(responseCode = "200", description = "Bo'lim yangilandi")
    @PutMapping("/{id}")
    public ResponseEntity<DepartmentDto> updateDepartment(
            @Parameter(description = "Bo'lim ID") @PathVariable Long id,
            @Valid @RequestBody CreateDepartmentRequest request) {
        return ResponseEntity.ok(departmentService.updateDepartment(id, request));
    }

    @Operation(summary = "Bo'limni o'chirish", description = "Faqat admin o'chira oladi.")
    @ApiResponse(responseCode = "204", description = "Bo'lim o'chirildi")
    @DeleteMapping("/{id}")
    public ResponseEntity<Void> deleteDepartment(
            @Parameter(description = "Bo'lim ID") @PathVariable Long id) {
        departmentService.deleteDepartment(id);
        return ResponseEntity.noContent().build();
    }

    // ─── A'zolar ──────────────────────────────────────────────────────────────

    @Operation(summary = "Bo'lim a'zolarini olish")
    @ApiResponse(responseCode = "200", description = "A'zolar ro'yxati qaytarildi")
    @GetMapping("/{id}/members")
    public ResponseEntity<List<DepartmentDto.MemberDto>> getMembers(
            @Parameter(description = "Bo'lim ID") @PathVariable Long id) {
        return ResponseEntity.ok(departmentService.getDepartmentMembers(id));
    }

    @Operation(summary = "Bo'limga a'zo qo'shish",
            description = "Admin yoki bo'lim boshlig'i a'zo qo'sha oladi. Rol: HEAD yoki MEMBER.")
    @ApiResponse(responseCode = "200", description = "A'zo qo'shildi")
    @PostMapping("/{id}/members")
    public ResponseEntity<DepartmentDto> addMember(
            @Parameter(description = "Bo'lim ID") @PathVariable Long id,
            @Valid @RequestBody AddDepartmentMemberRequest request) {
        return ResponseEntity.ok(departmentService.addMember(id, request));
    }

    @Operation(summary = "Bo'limdan a'zoni chiqarish")
    @ApiResponse(responseCode = "204", description = "A'zo chiqarildi")
    @DeleteMapping("/{id}/members/{userId}")
    public ResponseEntity<Void> removeMember(
            @Parameter(description = "Bo'lim ID") @PathVariable Long id,
            @Parameter(description = "Foydalanuvchi ID") @PathVariable Long userId) {
        departmentService.removeMember(id, userId);
        return ResponseEntity.noContent().build();
    }

    @Operation(summary = "A'zoning rolini o'zgartirish (HEAD / MEMBER)")
    @ApiResponse(responseCode = "200", description = "Rol o'zgartirildi")
    @PutMapping("/{id}/members/{userId}/role")
    public ResponseEntity<DepartmentDto> setMemberRole(
            @Parameter(description = "Bo'lim ID") @PathVariable Long id,
            @Parameter(description = "Foydalanuvchi ID") @PathVariable Long userId,
            @Parameter(description = "Yangi rol: HEAD yoki MEMBER")
            @RequestParam DepartmentRole role) {
        return ResponseEntity.ok(departmentService.setMemberRole(id, userId, role));
    }
}
