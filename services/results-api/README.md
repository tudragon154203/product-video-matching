# Results API Microservice

## Overview
This microservice provides a REST API for accessing and querying product-video matching results. It serves as the interface for users and other services to retrieve match information.

## Functionality
- Exposes REST endpoints for querying matching results.
- Allows filtering and sorting of matches based on various criteria.
- Provides access to match details, including evidence links.

## In/Out Events
### Input Events
- (Primarily consumes data from a database, not direct event inputs for core functionality)

### Output Events
- (Primarily serves API requests, not direct event outputs for core functionality)

## Current Progress
- Basic API endpoints for retrieving match lists.
- Integration with PostgreSQL database for data retrieval.

## What's Next
- Implement advanced search and filtering capabilities.
- Add pagination and sorting options for large result sets.
- Enhance API security and authentication.