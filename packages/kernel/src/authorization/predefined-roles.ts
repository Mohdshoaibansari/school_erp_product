export interface PredefinedRole {
  name: string;
  description: string;
  isSystem: boolean;
  permissions: string[];
}

export interface PredefinedPermission {
  code: string;
  name: string;
  description: string;
}

// Predefined permissions for the system
export const PREDEFINED_PERMISSIONS: PredefinedPermission[] = [
  // Institution management
  { code: 'institution.manage', name: 'Manage Institution', description: 'Full institution management' },
  { code: 'institution.view', name: 'View Institution', description: 'View institution details' },
  
  // User management
  { code: 'users.manage', name: 'Manage Users', description: 'Create, update, delete users' },
  { code: 'users.view', name: 'View Users', description: 'View user list and details' },
  { code: 'users.invite', name: 'Invite Users', description: 'Send user invitations' },
  
  // Academic management
  { code: 'academic.manage', name: 'Manage Academic', description: 'Manage academic structure' },
  { code: 'academic.view', name: 'View Academic', description: 'View academic structure' },
  
  // Student management
  { code: 'students.manage', name: 'Manage Students', description: 'Full student management' },
  { code: 'students.view', name: 'View Students', description: 'View student list and details' },
  { code: 'students.enroll', name: 'Enroll Students', description: 'Enroll new students' },
  
  // Attendance
  { code: 'attendance.manage', name: 'Manage Attendance', description: 'Full attendance management' },
  { code: 'attendance.mark', name: 'Mark Attendance', description: 'Mark daily attendance' },
  { code: 'attendance.view', name: 'View Attendance', description: 'View attendance records' },
  
  // Fees
  { code: 'fees.manage', name: 'Manage Fees', description: 'Full fee management' },
  { code: 'fees.collect', name: 'Collect Fees', description: 'Collect fee payments' },
  { code: 'fees.view', name: 'View Fees', description: 'View fee records' },
  
  // Reports
  { code: 'reports.manage', name: 'Manage Reports', description: 'Create and manage reports' },
  { code: 'reports.view', name: 'View Reports', description: 'View reports' },
  
  // Roles
  { code: 'roles.manage', name: 'Manage Roles', description: 'Create and manage roles' },
  { code: 'roles.assign', name: 'Assign Roles', description: 'Assign roles to users' },
  
  // Communication
  { code: 'communication.manage', name: 'Manage Communication', description: 'Full communication management' },
  { code: 'communication.send', name: 'Send Messages', description: 'Send messages to users' },
  { code: 'communication.view', name: 'View Messages', description: 'View messages' },
  
  // Calendar
  { code: 'calendar.manage', name: 'Manage Calendar', description: 'Manage calendar events' },
  { code: 'calendar.view', name: 'View Calendar', description: 'View calendar events' },
  
  // Config
  { code: 'config.manage', name: 'Manage Config', description: 'Manage system configuration' },
  { code: 'config.view', name: 'View Config', description: 'View system configuration' },
];

// Predefined roles with their permissions
export const PREDEFINED_ROLES: PredefinedRole[] = [
  {
    name: 'Director',
    description: 'Full system access with all permissions',
    isSystem: true,
    permissions: PREDEFINED_PERMISSIONS.map((p) => p.code),
  },
  {
    name: 'Principal',
    description: 'School-level management with most permissions',
    isSystem: true,
    permissions: [
      'institution.view',
      'users.manage',
      'users.view',
      'users.invite',
      'academic.manage',
      'academic.view',
      'students.manage',
      'students.view',
      'students.enroll',
      'attendance.manage',
      'attendance.mark',
      'attendance.view',
      'fees.manage',
      'fees.collect',
      'fees.view',
      'reports.manage',
      'reports.view',
      'roles.assign',
      'communication.manage',
      'communication.send',
      'communication.view',
      'calendar.manage',
      'calendar.view',
      'config.view',
    ],
  },
  {
    name: 'Teacher',
    description: 'Class-level management for teaching activities',
    isSystem: true,
    permissions: [
      'institution.view',
      'users.view',
      'academic.view',
      'students.view',
      'attendance.mark',
      'attendance.view',
      'reports.view',
      'communication.send',
      'communication.view',
      'calendar.view',
    ],
  },
  {
    name: 'Parent',
    description: 'View access for parent portal',
    isSystem: true,
    permissions: [
      'institution.view',
      'students.view',
      'attendance.view',
      'fees.view',
      'reports.view',
      'communication.view',
      'calendar.view',
    ],
  },
  {
    name: 'Student',
    description: 'Limited view access for student portal',
    isSystem: true,
    permissions: [
      'institution.view',
      'attendance.view',
      'fees.view',
      'reports.view',
      'communication.view',
      'calendar.view',
    ],
  },
];
