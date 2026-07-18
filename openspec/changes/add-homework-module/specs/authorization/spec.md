# Authorization — MODIFIED (Homework)

10 new permission rows + ~15 role_permission rows. No C-04 code changes.

Permissions: homework.read/create/update/delete/close, submission.read/create, grade.read/create/update.

Role mappings: Teacher (all 10), HOD/Principal/Admin (read-only: homework.read, submission.read, grade.read), Student (homework.read, submission.read, submission.create, grade.read).
