# Changelog

All notable changes to this project will be documented in this file.

This file is auto-generated from conventional commits using [git-cliff](https://git-cliff.org/).

## [0.1.87] - 2025-12-19


### Bug Fixes

- Update bandit config to skip B324 (MD5 for cache keys)
- Add type ignore comment for __init__ access


### Features

- Add deprecation policy and helpers


### Miscellaneous

- Track poetry.lock in git for reproducible builds

## [0.1.84] - 2025-12-18


### Other Changes

- Refactor type hints to use union syntax for optional types across multiple modules

## [0.1.83] - 2025-12-18


### Other Changes

- Remove flake8-type-checking rule from select options in pyproject.toml

## [0.1.82] - 2025-12-18


### Other Changes

- Refactor test imports and improve exception handling in unit tests

- Updated exception handling in investment model tests to raise ValueError instead of a generic Exception.
- Cleaned up import statements across various test files for consistency and readability.
- Replaced timezone.utc with UTC in datetime instances for better clarity and consistency.
- Enhanced test assertions to use `next()` for fetching specific tax documents, improving readability.
- Removed unnecessary blank lines and organized imports to follow PEP 8 guidelines.
- Refactor imports and improve type casting across multiple modules

- Reorganized import statements for better readability and consistency.
- Updated type casting to use string literals for type hints in various files.
- Enhanced error handling messages in SnapTrade provider.
- Adjusted datetime handling to use UTC consistently across market data providers.
- Cleaned up unused imports and improved code structure in recurring and tax modules.
- Ensured all FastAPI app functions specify return types accurately.

## [0.1.81] - 2025-12-18


### Other Changes

- Refactor type hints to use built-in `list` and `dict` instead of `List` and `Dict` from typing module across multiple files. Update imports to use collections.abc for Iterable and Sequence where applicable. This improves code readability and aligns with Python 3.9+ standards.

## [0.1.80] - 2025-12-18


### Documentation

- Update changelog [skip ci]


### Features

- Enhance decimal precision tests to demonstrate float precision issues
- Update documentation and deprecate clients module; introduce provider ABCs
- Enhance documentation and error handling guides; add migration and API reference sections


### Other Changes

- Add comprehensive unit tests for financial edge cases

- Implement tests for decimal precision, negative balances, fractional shares, and edge case amounts in test_financial_edge_cases.py.
- Introduce extended tests covering currency edge cases, order partial fills, date boundary issues, and leap year/DST transitions in test_financial_edge_cases_extended.py.
- Ensure robust handling of extreme values and edge scenarios in financial calculations.

## [0.1.79] - 2025-12-18


### Features

- Expand unit tests for cashflow calculations with comprehensive NPV and IRR scenarios

## [0.1.78] - 2025-12-18


### Features

- Add integration tests for market data providers and Plaid sandbox


### Styling

- Fix ruff formatting in test_plaid_sandbox.py

## [0.1.77] - 2025-12-17


### Bug Fixes

- Disable warning for unused ignores in mypy configuration

## [0.1.76] - 2025-12-17


### Documentation

- Update documentation for Yahoo Finance provider to include yahooquery package requirement

## [0.1.75] - 2025-12-17


### Testing

- Add checks for optional dependencies in unit tests for Plaid, Yahoo, and CCXT providers

## [0.1.73] - 2025-12-17


### Bug Fixes

- Update URLs in pyproject.toml to reflect correct repository links


### Refactor

- Update provider imports to handle missing dependencies gracefully and enhance documentation

## [0.1.72] - 2025-12-17


### Refactor

- Replace print statements with logging in categorization and insights modules

## [0.1.71] - 2025-12-17


### Bug Fixes

- Remove checkmarks from print statements in cashflows, chat, and insights modules

## [0.1.70] - 2025-12-17


### Bug Fixes

- Match CI config exactly (use ruff defaults)

## [0.1.69] - 2025-12-17


### Miscellaneous

- Remove mypy from hooks (use CI instead)

## [0.1.68] - 2025-12-17


### Bug Fixes

- Apply ruff formatting + switch pre-commit from black to ruff
- Add timeout handling to Yahoo Finance acceptance tests


### Features

- Update mypy configuration for improved type checking and dependencies
- Implement CI workflow for automated testing and linting

## [0.1.67] - 2025-12-16


### Features

- Add automated docs changelog generation workflow and script

## [0.1.66] - 2025-12-16


### Other Changes

- Refactor tests for improved readability and consistency

- Simplified the app creation in `test_analytics_api.py` by removing unnecessary variable assignment.
- Cleaned up whitespace and formatting in `test_budgets_api.py`, `test_documents_api.py`, `test_goals_api.py`, and other test files for better readability.
- Consolidated mock session and principal definitions in multiple test files to reduce redundancy.
- Adjusted function calls in various tests to remove unnecessary variable assignments.
- Removed commented-out code and unused imports across multiple test files.
- Enhanced clarity in assertions and method calls in tests related to investments, banking, and credit.

## [0.1.65] - 2025-12-15


### Refactor

- Improve type safety with type ignores for ai-infra LLM imports and enhance insights generation error handling

## [0.1.64] - 2025-12-15


### Refactor

- Enhance type safety and compatibility across multiple modules

## [0.1.63] - 2025-12-14


### Refactor

- Add type casting for improved type safety across multiple modules

## [0.1.62] - 2025-12-14


### Refactor

- Update references from CoreLLM to LLM and clean up type ignores across the codebase

## [0.1.61] - 2025-12-14


### Other Changes

- Replace CoreLLM with LLM across the codebase

- Updated documentation to reflect the transition from CoreLLM to LLM for intelligent analysis and insights.
- Modified imports and references in various modules including analytics, categorization, chat, crypto, goals, net worth, recurring, and tax.
- Adjusted unit and integration tests to mock LLM instead of CoreLLM.
- Enhanced LLM-powered features in recurring detection with optional capabilities for merchant normalization, variable amount detection, and subscription insights.
- Ensured backward compatibility by maintaining graceful degradation to rule-based logic when LLM is unavailable.

## [0.1.60] - 2025-12-14


### Refactor

- Remove net worth scaffolding and related CRUD resources from documentation

## [0.1.59] - 2025-12-14


### Other Changes

- Remove edge case tests for scaffold module and add unified exception hierarchy

## [0.1.58] - 2025-12-14


### Refactor

- Standardize environment variable naming and enhance FCRA compliance logging

## [0.1.57] - 2025-12-14


### Features

- Enhance financial precision across models and documentation

## [0.1.56] - 2025-12-12


### Miscellaneous

- Trigger pypi publish
- Re-trigger pypi publish after enabling workflow
- Trigger pypi publish


### Other Changes

- Fix repository links to point to nfraxlab organization

## [0.1.55] - 2025-12-10


### Other Changes

- Update dependencies in pyproject.toml and clean up .gitignore

## [0.1.54] - 2025-12-10


### Other Changes

- Add MIT License to the repository

## [0.1.53] - 2025-12-04


### Other Changes

- Fix formatting of badge links in README.md for improved readability

## [0.1.52] - 2025-12-04


### Other Changes

- Refactor README.md for clarity and organization; update feature descriptions and installation instructions

## [0.1.51] - 2025-11-29


### Other Changes

- Refactor documentation:
- Removed outdated references to the Persistence Strategy ADR in core-vs-scaffold.md and persistence.md.
- Updated solution guidance for LLM cost measurement in net-worth.md.
- Removed Easy Builders section from providers.md.
- Added comprehensive Banking Integration Guide with detailed setup, provider comparison, authentication methods, core operations, FastAPI integration, security practices, and troubleshooting tips.

## [0.1.50] - 2025-11-29


### Other Changes

- Remove outdated documentation and security guidelines; consolidate transaction categorization research and progress reports

## [0.1.49] - 2025-11-28


### Bug Fixes

- Correct documentation paths from src/fin_infra/docs to docs/
- Correct svc-infra documentation paths

## [0.1.48] - 2025-11-27


### Other Changes

- Add tax data integration documentation and security guidelines for sensitive files

## [0.1.47] - 2025-11-24


### Features

- Improve transaction date handling in InvestmentTransaction

## [0.1.46] - 2025-11-23


### Features

- Remove holdings and net worth scaffolding, update CLI commands for goals

## [0.1.45] - 2025-11-21


### Features

- Handle None close_price in security transformation

## [0.1.44] - 2025-11-21


### Features

- Refactor investment provider usage for improved clarity and maintainability

## [0.1.43] - 2025-11-21


### Features

- Refactor identity import for improved type handling in investment endpoints

## [0.1.42] - 2025-11-21


### Features

- Enhance authentication for investment endpoints and update request handling

## [0.1.41] - 2025-11-21


### Features

- Scaffold holdings domain with repository pattern and Pydantic schemas

## [0.1.40] - 2025-11-21


### Features

- Update add_investments to require user authentication and adjust tests accordingly


### Other Changes

- Add acceptance tests for Plaid investments integration and unit tests for portfolio analytics

- Implemented acceptance tests for the investments module using Plaid's sandbox environment, covering functionalities such as fetching holdings, transactions, investment accounts, and asset allocation.
- Added error handling tests for invalid access tokens and missing credentials.
- Documented Plaid sandbox setup instructions and rate limits for developers.
- Created unit tests for portfolio analytics, including metrics calculations, day change calculations, and asset allocation from holdings.
- Ensured comprehensive coverage for various scenarios, including empty holdings and holdings without cost basis.

## [0.1.39] - 2025-11-20


### Other Changes

- Add comprehensive unit tests for investment models and endpoints

- Implemented unit tests for the investments FastAPI integration in `test_add.py`, covering all API endpoints with mocked InvestmentProvider.
- Created unit tests for the `easy_investments()` function in `test_ease_investments.py`, including auto-detection of providers and error handling.
- Developed tests for financial data models in `test_financial_models.py`, validating creation, serialization, and integration of Account, Transaction, Quote, Candle, and Money models.
- Implement investment module with FastAPI integration and Pydantic models

- Added `add.py` for FastAPI integration with investment endpoints.
- Created `models.py` defining Pydantic models for securities, holdings, transactions, accounts, and asset allocation.
- Introduced `base.py` with abstract class `InvestmentProvider` for investment aggregation providers.
- Implemented `__init__.py` for provider package structure.
- Developed unit tests for all models in `test_models.py` to ensure data integrity and validation.

## [0.1.38] - 2025-11-20


### Features

- Expand products in create_link_token for comprehensive financial data access

## [0.1.37] - 2025-11-19


### Features

- Add backward compatibility for older svc-infra versions and improve error handling
- Enhance financial document management with OCR and AI analysis demos

## [0.1.36] - 2025-11-18


### Other Changes

- Refactor document handling and testing for financial documents

- Updated the growth multiple assertion in projections integration test to allow for higher contributions.
- Refactored document API tests to use MemoryBackend for in-memory storage, improving test isolation.
- Enhanced document upload functionality to include tax_year and form_type in metadata.
- Converted several synchronous test methods to asynchronous to align with updated document handling methods.
- Improved assertions in document tests to check for required metadata fields.
- Added tests for document analysis and extraction to ensure proper functionality and caching behavior.
- Updated document storage tests to utilize MemoryBackend, ensuring tests do not rely on external storage.
- Ensured all document-related tests are consistent with the new metadata structure and async handling.

## [0.1.35] - 2025-11-16


### Features

- Add connection utilities and reorganize docs

## [0.1.34] - 2025-11-16


### Refactor

- Remove scoped docs registration from add categorization function

## [0.1.33] - 2025-11-16


### Refactor

- Remove scoped docs registration from analytics and net worth modules

## [0.1.32] - 2025-11-15


### Refactor

- Remove scoped docs registration from multiple modules

## [0.1.31] - 2025-11-15


### Bug Fixes

- Map development environment to sandbox in PlaidClient

## [0.1.30] - 2025-11-15


### Features

- Update PlaidClient to use new SDK structure and improve error handling

## [0.1.29] - 2025-11-15


### Features

- Refactor PlaidClient initialization to support individual parameters alongside Settings object

## [0.1.28] - 2025-11-15


### Features

- Rename PlaidBanking to PlaidClient and implement transactions, balances, and identity methods

## [0.1.27] - 2025-11-14


### Features

- Update fin-infra to allow nullable user_id and tenant_id fields for easier testing and development

## [0.1.26] - 2025-11-13


### Other Changes

- Update .gitignore to include documentation files for agents and planning

## [0.1.25] - 2025-11-13


### Features

- Implement comprehensive fin-web API coverage analysis documentation

## [0.1.24] - 2025-11-13


### Features

- Update Makefile and quick_setup.py for improved dependency management and migration process


### Other Changes

- Update Makefile and quick_setup.py for improved dependency mana…

## [0.1.23] - 2025-11-12


### Bug Fixes

- Update field names in financial model tests for consistency; add comprehensive schema validation tests for all models


### Features

- Add mock user and session dependencies for acceptance tests in budget module
- Enhance test coverage with mock user and session dependencies in budget tests
- Add quick setup and scaffold models scripts for fin-infra template


### Other Changes

- Merge pull request #20 from Aliikhatami94/v1/example-template

V1/example template
- Remove outdated planning methodology and comprehensive template project implementation plan from the repository.
- Refactor code structure for improved readability and maintainability
- Remove measure_recurring_costs script and add test_providers script for validating provider connections; delete web-api-phase1-demo script to streamline examples.
- Refactor FastAPI routers to use svc-infra dual routers for authentication across multiple modules

- Updated `add_budgets` to use `user_router` for user-specific budget management.
- Introduced `cashflows` module with endpoints for financial calculations (NPV, IRR, PMT, FV, PV) using `public_router`.
- Modified `add_categorization` to utilize `public_router` for categorization statistics.
- Refactored `add_financial_conversation` to integrate AI-powered financial chat with user authentication.
- Adjusted `add_documents` to ensure public access to documentation endpoints before router mounting.
- Updated `add_goals` to use `user_router` for user-specific goal management.
- Implemented `add_insights` for user insights feed with authentication.
- Refined `add_net_worth_tracking` to use `user_router` for net worth tracking.
- Added `add_normalization` for symbol resolution and currency conversion with public access.
- Enhanced `add_recurring_detection` to utilize `user_router` for recurring detection.
- Updated `add_tax_data` to ensure user-specific tax data handling with proper documentation access.

## [0.1.22] - 2025-11-12


### Features

- Implement comprehensive FastAPI application for fin-infra-template


### Other Changes

- Implement comprehensive FastAPI application for fin-infra-template

## [0.1.21] - 2025-11-11


### Other Changes

- Merge pull request #18 from Aliikhatami94/v1/example-template

V1/example template
- Merge branch 'main' into v1/example-template

## [0.1.20] - 2025-11-11


### Features

- Update completion tracking for all phases; mark tasks as complete and provide final statistics
- Complete Phase 3 with advanced features including Portfolio Rebalancing, Unified Insights Feed, Crypto Insights, and Scenario Modeling; enhance documentation and coverage analysis


### Other Changes

- Complete Phase 3 with advanced features including Portfolio Reb…

## [0.1.19] - 2025-11-11


### Features

- Implement personalized crypto insights using ai-infra LLM
- Update Phase 3 Advanced Features Completion Checklist with testing status for Portfolio Rebalancing and Insights Feed
- Implement unified insights feed aggregator
- Complete Phase 2 verification and documentation, including tax-loss harvesting capabilities and updated README
- Implement in-memory document storage operations
- Implement document management module with upload, storage, OCR, and AI analysis capabilities
- Implement recurring summary endpoint with comprehensive documentation and integration tests
- Add balance history endpoint with trend analysis and statistics
- Complete Phase 1 implementation of fin-infra-web API coverage analysis
- Verify API compliance for goal management and update documentation
- Remove goals_demo.py as part of project restructuring
- Enhance API coverage with integration tests for goal management and funding allocation
- Implement funding allocation for financial goals
- Update milestone module tests and fix failing cases
- Introduce enhanced financial goal models with milestone tracking and funding allocation
- Complete Module 2.5 for persistence strategy and scaffold CLI with full documentation and quality verification
- Complete persistence documentation in `src/fin_infra/docs/persistence.md`
- Enhance persistence documentation and update TODO comments across multiple modules
- Complete net worth scaffold implementation with unit tests and template fixes
- Implement goals scaffold generation and unit tests


### Other Changes

- Merge pull request #16 from Aliikhatami94/feat/web-api-coverage

Feat/web api coverage
- Refactor test assertions for improved readability and consistency

- Updated assertion formatting in `test_provider_registry.py` for clarity.
- Simplified assertions in `test_recurring_detectors_llm.py` and `test_recurring_insights.py` to enhance readability.
- Cleaned up whitespace in multiple test files for consistency.
- Removed unused imports in `test_recurring_insights.py` and `test_recurring_normalizers.py`.
- Enhanced test cases in `test_security.py` for better structure and readability.
- Adjusted assertions in `test_tax.py` to improve clarity and maintainability.
- Ensured consistent formatting across all test files for better code quality.
- Add Unified Insights Feed documentation and enhance aggregator logic

- Introduced comprehensive documentation for the Unified Insights Feed, detailing its architecture, data models, public API, and insight generation logic.
- Updated the aggregator.py file to improve type annotations and ensure consistent use of Decimal for financial calculations in net worth and goal insights.
- Enhanced budget insights generation to initialize the insights list with explicit type.
- Refactored goal insights calculation to convert float values to Decimal for accuracy.
- Refactor and clean up recurring detection and banking history modules

- Removed unnecessary whitespace and improved code formatting for better readability in `history.py`.
- Updated import statements in `add.py` to use `RecurringDetector` instead of `SubscriptionInsights`.
- Enhanced `PatternDetector` class in `detector.py` by consolidating method definitions and improving logic flow.
- Streamlined logging messages in `detectors_llm.py` for clarity.
- Simplified JSON prompt formatting in `insights.py`.
- Consolidated field definitions in `models.py` for better clarity and consistency.
- Improved fuzzy matching logic in `normalizer.py` and updated known merchant groups for better accuracy.
- Enhanced summary generation logic in `summary.py` to improve clarity and maintainability.
- Updated test cases in `test_recurring_api.py` to utilize public router for testing without authentication.
- Add integration and unit tests for tax-loss harvesting (TLH) functionality

- Implemented integration tests for TLH API endpoints, covering scenarios for getting TLH opportunities and simulating TLH scenarios.
- Added unit tests for TLH logic, including opportunity and scenario models, wash sale risk assessment, and recommendation generation.
- Ensured existing tax API endpoints remain functional with new tests.
- Created fixtures for sample positions and recent trades to facilitate testing.
- Add document management documentation and update API tests

- Created comprehensive documentation for the document management system, covering features, usage, architecture, API reference, and troubleshooting.
- Updated the document upload API endpoint to accept a single request dictionary for easier testing.
- Modified the test client to suppress server exceptions for better error handling during tests.
- Adjusted assertions in the document deletion test to expect any error status when a document is not found.
- Implement banking balance history tracking and enhance transaction filtering

- Added a new module for account balance history tracking, allowing recording and retrieval of historical balance snapshots.
- Implemented functions to record, retrieve, and delete balance snapshots with in-memory storage for testing.
- Created unit tests for balance history functionalities, ensuring correct behavior for recording, retrieving, and deleting snapshots.
- Developed integration tests for banking API endpoints, focusing on transaction filtering by various criteria (merchant, category, amount, tags, etc.).
- Updated existing unit tests for banking transactions to accommodate new pagination envelope format.
- Add comprehensive goal management documentation

- Introduced detailed documentation for the goal management module, covering:
  - Overview of goal types and statuses
  - Key features including milestone tracking and funding allocation
  - Quick start guide with code examples for basic setup, milestone tracking, and funding allocation
  - Core concepts detailing goal types, statuses, milestones, and funding allocation
  - Progress tracking methods for goals and milestones
  - API reference with CRUD operations and endpoints
  - Integration patterns with svc-infra and other modules
  - Best practices for goal design, funding allocation, and progress tracking
  - Testing guidelines including unit and integration tests
  - Architecture decisions and future enhancements
  - Troubleshooting tips for common issues
- Add unit tests for goal management and milestone tracking

- Created `test_management.py` to cover CRUD operations for goals including creation, listing, retrieval, updating, deletion, and progress tracking.
- Implemented tests for goal creation validation, filtering goals by user ID, type, and status, and ensuring proper error handling.
- Added `test_milestones.py` to validate milestone functionality including adding milestones, checking reached milestones, generating celebration messages, and tracking progress.
- Included integration tests to verify the complete lifecycle of goals and milestones.
- Add security guidelines and comprehensive tests for scaffold module

- Created `teller-security.md` to outline security best practices, prohibited files, and emergency procedures for handling secrets.
- Added integration tests for the scaffold CLI, covering help text, valid and invalid domains, flag behavior, and edge cases.
- Implemented integration tests for the full scaffold workflow, including compile and import tests (with known issues documented).
- Developed unit tests for edge cases in the scaffold module, focusing on invalid inputs, file overwrite behavior, conditional field generation, and custom filenames.
- Ensured all tests validate file content quality, error messages, and proper imports.

## [0.1.18] - 2025-11-08


### Features

- Add net worth scaffold templates for tracking financial snapshots
- Implement budget scaffold with repository pattern
- Add financial planning conversation capabilities


### Other Changes

- Merge pull request #15 from Aliikhatami94/feat/web-api-coverage

Feat/web api coverage
- Add persistence strategy documentation and scaffolding CLI for fin-infra

- Introduced `presistence-strategy.md` outlining the decision for applications to own their persistence layer.
- Provided detailed analysis and rationale for the chosen approach.
- Implemented scaffolding CLI commands to generate SQLAlchemy models, Pydantic schemas, and repository patterns for various domains (budgets, goals, net worth).
- Created utility functions for template rendering and file operations.
- Added templates for budgets domain including models, schemas, and repository patterns.
- Documented the scaffolding process and usage in `docs/persistence.md`.
- Updated existing TODO comments to reflect the new persistence strategy.

## [0.1.17] - 2025-11-08


### Bug Fixes

- Remove TODO stubs from __init__.py - import actual implementations


### Documentation

- Mark budgets integration and acceptance tests complete
- Complete Task 18 - Comprehensive budget management documentation
- Mark Task 10 fully complete
- Complete Task 10 - comprehensive documentation


### Features

- Complete Task 17 - Implement add_budgets() FastAPI helper
- Complete Task 16 - Implement easy_budgets() builder
- Complete Task 15 - Implement budget templates
- Complete Task 14 - Implement budget alerts
- Complete Task 13 - Implement BudgetTracker class
- Complete Task 12 - Define all Pydantic models
- Complete Task 11 - Create budgets module structure


### Miscellaneous

- Update Task 18 completion checklist - budget module ready


### Other Changes

- Merge pull request #14 from Aliikhatami94/feat/web-api-coverage

Feat/web api coverage


### Testing

- Complete integration and acceptance tests

## [0.1.16] - 2025-11-08


### Bug Fixes

- Fix projection realistic values test and add Alpha Vantage rate limit handling


### Build

- Add integration tests to make test command


### Features

- Complete Task 9 - Create add_analytics() FastAPI helper
- Complete Task 8 - Create easy_analytics() builder
- Complete Task 7 - Implement growth projections
- Complete Task 6 - Implement portfolio analytics
- Add LLM-powered spending insights (Task 5 optional)
- Complete Task 5 - Implement spending insights


### Other Changes

- Merge pull request #13 from Aliikhatami94/feat/web-api-coverage

Feat/web api coverage

## [0.1.15] - 2025-11-08


### Documentation

- Fix README markdown formatting issues
- Add mandatory testing & documentation requirements to all tasks
- Update copilot and plans documentation to include ai-infra integration and standards


### Features

- Complete Task 4 - Implement savings rate calculation
- Complete Task 3 - Implement cash flow analysis
- Complete Tasks 1-2 - Create analytics module structure and models
- Add Section 27 - Web Application API Coverage
- Add comprehensive fin-infra-template example project (Phases 1-2)


### Other Changes

- Merge pull request #12 from Aliikhatami94/feat/web-api-coverage

Feat/web api coverage


### Refactor

- Reorganize plans.md for clarity and actionability
- Remove Alembic configuration and migration scripts


### Testing

- Add integration tests for Tasks 3 & 4

## [0.1.14] - 2025-11-07


### Bug Fixes

- Correct path to wait_for.py script in Makefile


### Features

- Add LLM cost measurement script and update documentation for V2 insights
- Implement LLM endpoints for insights and conversation handling, update tests and documentation
- Add V2 endpoints for financial insights and conversation handling with structured request/response models
- Refactor conversation handling for natural dialogue and update API patterns documentation
- Add conversation architecture audit documentation and findings
- Add LLM-generated financial insights for net worth tracking
- Enhance easy_net_worth with LLM support and update documentation
- Add benchmarking and cost measurement scripts for recurring detection
- Introduce LLM-enhanced recurring detection (V2)
- Update SubscriptionInsights model to improve field descriptions and constraints
- Implement LLM-based variable amount detection, subscription insights generation, and merchant name normalization
- Enhance easy_recurring_detection with LLM support for merchant normalization and variable detection


### Other Changes

- Merge pull request #11 from Aliikhatami94/feat/prod-readiness-v1

Feat/prod readiness v1
- Add verification guide for Recurring Detection V2 and Net Worth LLM Insights research documentation

- Introduced a comprehensive verification guide for Recurring Detection V2, detailing accuracy benchmarks, cost measurements, and a production verification checklist.
- Added a new research document for Net Worth LLM Insights, outlining structured output capabilities, financial insights generation, multi-turn conversation management, and goal tracking with validation.
- Included detailed examples, schemas, and cost projections to ensure clarity and usability for developers and stakeholders.
- Add unit tests for recurring insights and normalizers

- Implemented comprehensive unit tests for SubscriptionInsights and SubscriptionInsightsGenerator in `test_recurring_insights.py`, covering model validation, insights generation, caching behavior, and budget tracking.
- Added unit tests for MerchantNormalized and MerchantNormalizer in `test_recurring_normalizers.py`, focusing on merchant name normalization, confidence validation, caching, and fallback mechanisms.
- Ensured tests cover various scenarios including cache hits/misses, error handling, and budget management.

## [0.1.13] - 2025-11-07


### Features

- Update documentation and add acceptance tests for LLM-based categorization (V2)
- Add net worth calculator module with core functions
- Add net worth tracking module with models and API integration
- Enhance net worth tracking with comprehensive V1 implementation
- Implement recurring transaction detection engine
- Complete Section 15 V1 - Transaction Categorization
- Complete V1 implementation of transaction categorization
- Implement hybrid transaction categorization engine
- Enhance Tax Data Integration with real IRS and TaxBit provider implementations
- Implement TaxBitProvider for cryptocurrency tax calculations


### Other Changes

- Merge pull request #10 from Aliikhatami94/feat/prod-readiness-v1

Feat/prod readiness v1
- Refactor tests to support async categorization and add LLM categorization tests

- Updated existing unit tests in `test_categorization.py` to use async/await syntax for categorization functions.
- Added new test suite `test_llm_categorization.py` to cover LLM-based categorization, including:
  - Basic categorization with structured output.
  - Retry logic for transient failures.
  - Budget tracking and cost enforcement.
  - Graceful fallback to sklearn when LLM fails.
  - Hybrid flow testing (exact → regex → sklearn → LLM).
- Add recurring transaction detection research documentation and models

- Introduced a comprehensive markdown document detailing the research on recurring transaction detection, including algorithms, heuristics, and implementation plans.
- Added Pydantic models for recurring patterns, subscription detection results, bill predictions, and API request/response structures in `models.py`.
- Implemented merchant name normalization and fuzzy matching functionalities in `normalizer.py` to enhance merchant grouping and detection accuracy.
- Add ADR and research documentation for transaction categorization

- Introduced ADR-0018 detailing the architecture for transaction categorization, including context, requirements, decision rationale, and implementation plan.
- Added comprehensive research documentation comparing rule-based, machine learning, and hybrid approaches for merchant-to-category prediction.
- Outlined category taxonomy, merchant name normalization strategies, and pre-trained model options.
- Provided implementation plans for MVP, ML fallback, and active learning phases.

## [0.1.12] - 2025-11-06


### Bug Fixes

- Enhance market data documentation with FastAPI integration examples and comprehensive API reference
- Update banking documentation with comprehensive examples and remove outdated landing page fix summary


### Features

- Add Trivy ignore list for known CVEs in vendor images
- Complete research and design for tax data integration; implement provider architecture and data models
- Complete Experian API integration with OAuth 2.0, caching, and webhooks
- Implement Experian API integration with real data handling
- Implement credit score monitoring with Experian integration
- Implement comprehensive compliance tracking and documentation
- Enhance CI/CD quality gates with Trivy security scanning and comprehensive documentation
- Enhance fintech API demo with comprehensive documentation, environment setup, and integration patterns
- Add financial route classification and integration with svc-infra
- Implemented financial_route_classifier for automatic classification of financial API endpoints.
- Created compose_classifiers function to allow chaining of multiple classifiers.
- Added comprehensive tests for financial route classification and classifier composition.
- Updated documentation for observability integration and usage examples.
- Implement financial security module with PII masking, token encryption, and audit logging
- Implement data normalization module for financial symbols and currencies
- Add comprehensive documentation for caching, rate limiting, and retries integration with svc-infra
- Add brokerage integration with watchlist functionality
- Add brokerage module with Alpaca integration, including order and position models, and FastAPI routes
- Implement cryptocurrency market data module with CoinGecko integration and FastAPI support


### Other Changes

- Merge pull request #9 from Aliikhatami94/feat/prod-readiness-v1

Feat/prod readiness v1
- Credit updates
- Add unit tests for Experian client, parser, and provider

- Implement comprehensive unit tests for the Experian HTTP client, covering API request methods, error handling, retry logic, and OAuth token injection.
- Create unit tests for the Experian response parser, validating the parsing of credit scores, credit reports, accounts, inquiries, and public records, including edge cases.
- Develop unit tests for the Experian provider, ensuring proper integration with the client and parser, as well as error handling and context manager functionality.

## [0.1.11] - 2025-11-05


### Bug Fixes

- Move date import to module level to fix Pydantic forward reference error


### Other Changes

- Move date import to module level to fix Pydantic forward referen…

## [0.1.10] - 2025-11-05


### Bug Fixes

- Add required 'release' parameter to easy_service_app in test
- Move test_cards_app to acceptance tests directory
- Move docs to proper location in src/fin_infra/docs/
- Move test_cards_app.py to tests directory


### Features

- Add landing page cards for banking and market data capabilities


### Other Changes

- Merge pull request #7 from Aliikhatami94/feat/prod-readiness-v1

Feat/prod readiness v1

## [0.1.9] - 2025-11-05


### Other Changes

- Merge pull request #6 from Aliikhatami94/feat/prod-readiness-v1

Feat/prod readiness v1
- Merge branch 'main' into feat/prod-readiness-v1

## [0.1.6] - 2025-11-04


### Other Changes

- Update version to 0.1.5 in pyproject.toml and adjust API paths i…

## [0.1.5] - 2025-11-04


### Other Changes

- Enhance add_banking and add_market_data to accept provider inst…

## [0.1.4] - 2025-11-04


### Other Changes

- Update version to 0.1.2 and clean up dependencies in pyproject.toml

## [0.1.3] - 2025-11-04


### Other Changes

- Enhance Alpha Vantage and Yahoo Finan…

## [0.1.2] - 2025-11-04


### Bug Fixes

- Update version to 0.1.8 in pyproject.toml and adjust router imports in add_banking and add_market_data
- Update version to 0.1.5 in pyproject.toml and adjust API paths in add_banking and add_market_data
- Update version to 0.1.3 in pyproject.toml
- Update version to 0.1.2 and clean up dependencies in pyproject.toml
- Update AlphaVantageMarketData test to include API key requirement


### Documentation

- Add router and API standards for fin-infra capabilities, emphasizing svc-infra dual routers


### Features

- Enhance add_banking and add_market_data to accept provider instances directly


### Other Changes

- Merge pull request #1 from Aliikhatami94/feat/prod-readiness-v1

Feat/prod readiness v1
- Enhance Alpha Vantage and Yahoo Finance integration

- Updated Alpha Vantage provider to include detailed documentation, improved error handling, and added a search feature.
- Implemented basic rate limiting in Alpha Vantage to manage API request frequency.
- Enhanced Yahoo Finance provider with comprehensive documentation and improved quote and history retrieval methods.
- Added acceptance tests for both Alpha Vantage and Yahoo Finance providers to ensure functionality.
- Created unit tests for market data providers, including easy_market builder function and individual provider methods.
- Updated tests to reflect changes in provider class names and methods.
- Refactored code for better readability and maintainability.
- Merge branch 'main' into feat/prod-readiness-v1

## [0.1.1] - 2025-10-21


### Bug Fixes

- Update SBOM artifact naming to include profile for better clarity
- Remove unnecessary --no-root option from poetry install command


### Features

- Implement Banking Integration Architecture with Teller as default provider
- Add svc-infra as a dependency in pyproject.toml
- Clarify that fin-infra has no direct dependency on svc-infra at the package level
- Implement provider registry for dynamic loading and configuration of financial data providers; add comprehensive tests for registry functionality
- Add comprehensive unit tests for financial data models including Account, Transaction, Quote, Candle, and Money
- Enhance production readiness plan with easy setup functions and mandatory research protocol for fintech capabilities
- Add comprehensive documentation for agents, copilot instructions, plans, and ADR template with svc-infra reuse assessments
- Add comprehensive documentation for contributing, credit, market data, tax integration, and getting started
- Implement acceptance testing framework with Redis support and update documentation
- Initial commit of financial infrastructure toolkit

<!-- Generated by git-cliff -->
