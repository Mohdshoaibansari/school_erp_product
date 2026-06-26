import { PrismaClient, Role, Permission, RoleAssignment, OrgUnit } from '@school-erp/database';

export interface AssignRoleInput {
  userId: string;
  roleId: string;
  institutionId?: string;
  scopeType?: string;
  scopeId?: string;
}

export interface CheckPermissionInput {
  userId: string;
  permissionCode: string;
  institutionId?: string;
  scopeType?: string;
  scopeId?: string;
}

export interface CreateRoleInput {
  name: string;
  description?: string;
  permissionIds?: string[];
}

export interface CreatePermissionInput {
  code: string;
  name: string;
  description?: string;
}

export class AuthZService {
  constructor(private prisma: PrismaClient) {}

  async check(input: CheckPermissionInput): Promise<boolean> {
    const { userId, permissionCode, institutionId, scopeType, scopeId } = input;

    // Find all role assignments for this user
    const assignments = await this.prisma.roleAssignment.findMany({
      where: {
        userId,
        ...(institutionId ? { institutionId } : {}),
        ...(scopeType ? { scopeType } : {}),
        ...(scopeId ? { scopeId } : {}),
      },
      include: {
        role: {
          include: {
            permissions: {
              include: {
                permission: true,
              },
            },
          },
        },
      },
    });

    // Check if any role has the required permission
    for (const assignment of assignments) {
      const hasPermission = assignment.role.permissions.some(
        (rp) => rp.permission.code === permissionCode
      );
      if (hasPermission) {
        return true;
      }
    }

    return false;
  }

  async require(input: CheckPermissionInput): Promise<void> {
    const hasPermission = await this.check(input);
    if (!hasPermission) {
      throw new Error(
        `Permission denied: ${input.permissionCode} for user ${input.userId}`
      );
    }
  }

  async getUserPermissions(
    userId: string,
    institutionId?: string
  ): Promise<Permission[]> {
    const assignments = await this.prisma.roleAssignment.findMany({
      where: {
        userId,
        ...(institutionId ? { institutionId } : {}),
      },
      include: {
        role: {
          include: {
            permissions: {
              include: {
                permission: true,
              },
            },
          },
        },
      },
    });

    // Collect unique permissions
    const permissionMap = new Map<string, Permission>();
    for (const assignment of assignments) {
      for (const rp of assignment.role.permissions) {
        permissionMap.set(rp.permission.code, rp.permission);
      }
    }

    return Array.from(permissionMap.values());
  }

  async assignRole(input: AssignRoleInput): Promise<RoleAssignment> {
    // Verify role exists
    const role = await this.prisma.role.findFirst({
      where: { id: input.roleId },
    });
    if (!role) {
      throw new Error('Role not found');
    }

    // Verify user exists
    const user = await this.prisma.user.findFirst({
      where: { id: input.userId, deletedAt: null },
    });
    if (!user) {
      throw new Error('User not found');
    }

    // Check if assignment already exists
    const existing = await this.prisma.roleAssignment.findFirst({
      where: {
        userId: input.userId,
        roleId: input.roleId,
        institutionId: input.institutionId || null,
        scopeType: input.scopeType || null,
        scopeId: input.scopeId || null,
      },
    });

    if (existing) {
      throw new Error('Role assignment already exists');
    }

    return this.prisma.roleAssignment.create({
      data: {
        userId: input.userId,
        roleId: input.roleId,
        institutionId: input.institutionId,
        scopeType: input.scopeType,
        scopeId: input.scopeId,
      },
    });
  }

  async removeRole(
    userId: string,
    roleId: string,
    institutionId?: string
  ): Promise<void> {
    await this.prisma.roleAssignment.deleteMany({
      where: {
        userId,
        roleId,
        ...(institutionId ? { institutionId } : {}),
      },
    });
  }

  async getUserRoles(
    userId: string,
    institutionId?: string
  ): Promise<Role[]> {
    const assignments = await this.prisma.roleAssignment.findMany({
      where: {
        userId,
        ...(institutionId ? { institutionId } : {}),
      },
      include: {
        role: true,
      },
    });

    return assignments.map((a) => a.role);
  }

  async getRoles(tenantId: string): Promise<Role[]> {
    return this.prisma.role.findMany({
      where: { tenantId },
      include: {
        permissions: {
          include: {
            permission: true,
          },
        },
      },
    });
  }

  async createRole(
    tenantId: string,
    data: CreateRoleInput
  ): Promise<Role> {
    return this.prisma.role.create({
      data: {
        tenantId,
        name: data.name,
        description: data.description,
        permissions: data.permissionIds
          ? {
              create: data.permissionIds.map((id) => ({
                permissionId: id,
              })),
            }
          : undefined,
      },
      include: {
        permissions: {
          include: {
            permission: true,
          },
        },
      },
    });
  }

  async getPermissions(): Promise<Permission[]> {
    return this.prisma.permission.findMany();
  }

  async createPermission(data: CreatePermissionInput): Promise<Permission> {
    return this.prisma.permission.create({
      data,
    });
  }

  // Scope resolution methods
  async resolveUserScopes(
    userId: string,
    institutionId: string
  ): Promise<{
    institution: boolean;
    grades: string[];
    classes: string[];
  }> {
    const assignments = await this.prisma.roleAssignment.findMany({
      where: {
        userId,
        institutionId,
      },
      include: {
        role: true,
      },
    });

    const result = {
      institution: false,
      grades: [] as string[],
      classes: [] as string[],
    };

    for (const assignment of assignments) {
      // Check if user has institution-level access
      if (!assignment.scopeType && !assignment.scopeId) {
        result.institution = true;
      }

      // Check grade-level access
      if (assignment.scopeType === 'grade' && assignment.scopeId) {
        if (!result.grades.includes(assignment.scopeId)) {
          result.grades.push(assignment.scopeId);
        }
      }

      // Check class-level access
      if (assignment.scopeType === 'class' && assignment.scopeId) {
        if (!result.classes.includes(assignment.scopeId)) {
          result.classes.push(assignment.scopeId);
        }
      }
    }

    return result;
  }

  async checkScopedPermission(
    input: CheckPermissionInput & { orgUnitId?: string }
  ): Promise<boolean> {
    // First check if user has the permission at all
    const hasPermission = await this.check(input);
    if (!hasPermission) {
      return false;
    }

    // If no org unit specified, permission is at institution level
    if (!input.orgUnitId) {
      return true;
    }

    // Check if user has scope that includes the org unit
    const scopes = await this.resolveUserScopes(
      input.userId,
      input.institutionId!
    );

    // Institution-level access includes all org units
    if (scopes.institution) {
      return true;
    }

    // Get the org unit to check its hierarchy
    const orgUnit = await this.prisma.orgUnit.findUnique({
      where: { id: input.orgUnitId },
    });

    if (!orgUnit) {
      return false;
    }

    // Check if user has access to this specific org unit
    if (scopes.classes.includes(input.orgUnitId)) {
      return true;
    }

    // Check if user has access to the parent grade
    if (orgUnit.parentId && scopes.grades.includes(orgUnit.parentId)) {
      return true;
    }

    // Check if user has access to any ancestor
    let current = orgUnit;
    while (current.parentId) {
      if (scopes.grades.includes(current.parentId) || 
          scopes.classes.includes(current.parentId)) {
        return true;
      }
      current = await this.prisma.orgUnit.findUnique({
        where: { id: current.parentId },
      }) as OrgUnit;
    }

    return false;
  }

  async assignScopedRole(
    userId: string,
    roleId: string,
    institutionId: string,
    scopeType: 'institution' | 'grade' | 'class',
    scopeId?: string
  ): Promise<RoleAssignment> {
    // Verify the scope exists
    if (scopeId) {
      const orgUnit = await this.prisma.orgUnit.findUnique({
        where: { id: scopeId },
      });
      if (!orgUnit) {
        throw new Error('Org unit not found');
      }
    }

    return this.assignRole({
      userId,
      roleId,
      institutionId,
      scopeType,
      scopeId,
    });
  }
}
