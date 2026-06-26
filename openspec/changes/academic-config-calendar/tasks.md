## 1. Academic Structure Service (C-05)

- [x] 1.1 Define Prisma models: academic_years, terms, grades, classes, sections, subjects
- [x] 1.2 Implement AcademicService: getCurrentYear, getCurrentTerm, getGrades, getClasses
- [x] 1.3 Implement class management within grade hierarchy

## 2. Config & Rules Engine (C-08)

- [x] 2.1 Define Prisma models: config_keys, config_values with typed values
- [x] 2.2 Implement ConfigService: get, set with scope inheritance (platform → client → institution)
- [x] 2.3 Implement rule evaluation: config keys consumable by modules for decision logic
- [ ] 2.4 Implement config change audit trail (deferred to audit-notifications-communication change)

## 3. Calendar Service

- [x] 3.1 Define Prisma model: calendar_events with date, type, label
- [x] 3.2 Implement CalendarService: getToday, getDayType, isHoliday, getEventsInRange
- [x] 3.3 Support event types: school_day, holiday, exam_day, event
