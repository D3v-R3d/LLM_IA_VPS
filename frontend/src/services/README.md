# Services

This directory contains API service layer implementations.

## Structure

```
services/
├── apiClient.js      # HTTP client configuration
├── authService.js    # Authentication related services
├── chatService.js    # Chat related services
├── documentService.js # Document management services
└── README.md         # This file
```

## Service Layer Responsibilities

The service layer handles:
- API communication
- Request/response transformation
- Error handling and logging
- Authentication and authorization
- Caching strategies

## Implementation Patterns

Services follow these patterns:
- Single responsibility per service file
- Consistent error handling
- Type-safe request/response interfaces
- Mock data support for development
- Retry logic for transient failures

## Usage

Services are imported and used in components:

```javascript
import { getDocuments, uploadDocument } from '../services/documentService';

const documents = await getDocuments();
```

## HTTP Client

All services use a shared HTTP client (`apiClient.js`) that:
- Handles authentication headers
- Manages base URLs
- Implements request/response interceptors
- Provides consistent error handling