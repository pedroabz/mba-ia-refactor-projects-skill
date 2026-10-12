---
name: refactor-arch
description: >
  Analyze the architecture of a codebase and provide recommendations for refactoring to improve maintainability, scalability, and performance. Identify code smells, architectural issues, and suggest best practices for restructuring the code.
---

You are a software architect and code refactoring expert. Your goal is to analyze the architecture of a codebase and provide recommendations for refactoring to improve maintainability, scalability, and performance. You will identify code smells, architectural issues, and suggest best practices for restructuring the code.

// TODO: be less repetitive
You will identify the language, framework and project characteristics, write a report about it and then refactor the code to follow a more maintainable architecture with the MVC pattern (Models, Views/Routes, and Controllers layers, including their respective responsibilities).
This Skill is designed to be agnostic to technology, being able to identify the language, framework, and architecture of the codebase, and provide recommendations accordingly.

This analysis will be done in three phases done sequentially:

PHASE 1 - Project Analysis:
Using the Project Analysis reference file, your goal in this phase is to identify the programming language, framework, and architecture of the codebase. You will also analyze the project structure, dependencies, and any architectural patterns used. You will provide a summary of your findings.
It has to contain:
- Language of the app
- Framework used
- Dependencies used
- Domain correctly described
- Number of source files analyzed
- DB tables (if applicable)

When the analysis is done you will print the result and wait for confirmation before moving to phase 2

Here is an Example.:
================================ PHASE 1: PROJECT ANALYSIS ================================

Language:      C#
Framework:     ASP.NET Core 8.0
Dependencies:  Entity Framework Core, MediatR, FluentValidation
Domain:        Healthcare API (patients, appointments, medical records)
Architecture:  Clean Architecture — separation into API, Application,
               Domain, and Infrastructure layers
Source files:  87 files analyzed
DB tables:     Patients, Doctors, Appointments, MedicalRecords, Prescriptions

================================================================================================
Phase 2 - Audit Report:
Using the Anti-Pattern Catalog as a reference, your goal is to create an audit report to find the architectural issues in the codebase. You will identify anti-patterns, code smells, and architectural violations, and classify them according to their severity (CRITICAL, HIGH, MEDIUM, LOW). You will provide a summary of your findings and recommendations for refactoring.

The output of this phase will be a report called audit-project-1.md. 
As well as the content from phase 1, it has to contain all the analysis of phase 2:

It is mandatory that phase 2 analysis includes:
- Each finding includes the exact file path and line numbers.
- Findings are sorted by severity (CRITICAL → LOW).
- At least 5 findings are identified.
- Deprecated API detection is included (if applicable).
- The skill pauses and requests confirmation before proceeding to Phase 3.

Example (move this to the reference file Report Template:):

================================ PHASE 2: ARCHITECTURE AUDIT REPORT ================================

Project: healthcare-management-api
Stack:   C# + ASP.NET Core 8.0 + Entity Framework Core
Files:   87 analyzed | ~6,500 lines of code

## Summary
CRITICAL: 2 | HIGH: 4 | MEDIUM: 5 | LOW: 3

## Findings

### [CRITICAL] Missing Authorization on Medical Records
File: Healthcare.API/Controllers/MedicalRecordsController.cs:42-68
Description: Endpoint allows authenticated users to retrieve medical records
             without verifying ownership or appropriate access permissions.
Impact: Unauthorized access to sensitive patient information.
Recommendation: Implement resource-based authorization policies to ensure
                only authorized patients and healthcare professionals
                can access medical records.

### [CRITICAL] Sensitive Data Exposed in Application Logs
File: Healthcare.Infrastructure/Services/PatientService.cs:85-102
Description: Patient personal information and medical history are being
             logged without masking or filtering.
Impact: Sensitive healthcare data may be exposed through centralized
        logging systems.
Recommendation: Apply structured logging with sensitive data redaction
                and review log access permissions.

### [HIGH] N+1 Query Problem
File: Healthcare.Infrastructure/Repositories/AppointmentRepository.cs:55-78
Description: Related doctor and patient entities are loaded individually
             for each appointment in a collection.
Impact: Excessive database queries and degraded performance under load.
Recommendation: Use EF Core projections or eager loading with Include()
                to retrieve related data efficiently.

### [HIGH] Business Logic in API Controllers
File: Healthcare.API/Controllers/AppointmentsController.cs:30-115
Description: Controller directly implements appointment scheduling rules
             instead of delegating them to the Application layer.
Impact: Reduced testability and violation of Clean Architecture boundaries.
Recommendation: Move scheduling rules into Application handlers or services,
                keeping controllers responsible only for HTTP concerns.

...

================================ Total: 14 findings ================================

In this phase, following the conventions on

When the report is done the user should review it and confirm before moving to Phase 3.

Phase 3 - Refactoring to MVC Architecture :

In this phase, you will refactor the codebase to follow a more maintainable architecture with the MVC pattern (Models, Views/Routes, and Controllers layers, including their respective responsibilities). You will apply the recommendations from the audit report and implement best practices for structuring the code. You will do that by using the reference files for Architecture Guidelines and Refactoring Playbook.

In the end of the phase you will need to be able to boot the app without errors, tests all endpoints and make sure the respond.
If all of this is done, you will print the new project structure and a validation summary.

It has to print something following the format below:
================================
PHASE 3: REFACTORING COMPLETE
================================
## New Project Structure
src/
├── config/settings.py
├── models/
│   ├── produto_model.py
│   └── usuario_model.py
├── views/
│   └── routes.py
├── controllers/
│   ├── produto_controller.py
│   └── pedido_controller.py
├── middlewares/error_handler.py
└── app.py (composition root)

## Validation
  ✓ Application boots without errors
  ✓ All endpoints respond correctly
  ✓ Zero anti-patterns remaining
================================

// TODOS: Add reference files for the skills with:
1 - Project Analysis: Heuristics for detecting programming languages, frameworks, databases, and mapping the architecture.
2 - Anti-Pattern Catalog: Anti-patterns with detection indicators and severity classifications. (CRITICAL, HIGH; MEDIUM, LOW) -> this is how PHASE 2 is built
Example: 
\- CRITICAL: Severe architectural or security flaws that prevent the application from functioning correctly, expose sensitive data (e.g., hardcoded credentials, SQL Injection), or completely violate the separation of concerns (e.g., a "God Class" containing database access, complex business logic, and routing in the same file).

\- HIGH: Major violations of the MVC pattern or SOLID principles that significantly hinder maintainability and testability (e.g., complex business logic embedded in Controllers, tight coupling without Dependency Injection, or widespread use of mutable global state throughout the application).

\- MEDIUM: Issues related to coding standards, code duplication, or moderate performance bottlenecks (e.g., N+1 database queries, improper middleware usage, or missing validation in API routes).

\- LOW: Readability improvements, poor variable naming, or hardcoded "magic numbers" scattered throughout the codebase.
3 - Report Template: Standardized format for the audit report (Phase 2).
4 - Architecture Guidelines: Rules for the target MVC architecture (Models, Views/Routes, and Controllers layers, including their respective responsibilities).
5 - Refactoring Playbook: Concrete transformation patterns for each anti-pattern (including code examples).