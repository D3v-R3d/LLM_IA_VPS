# Components

This directory contains reusable UI components.

## Structure

```
components/
├── ui/               # Basic UI components (buttons, inputs, etc.)
├── layout/           # Layout components (headers, footers, etc.)
├── chat/             # Chat-related components
├── documents/        # Document-related components
└── README.md         # This file
```

## Component Guidelines

Components should follow these guidelines:
- Single responsibility principle
- Reusable and composable
- Properly typed with PropTypes or TypeScript
- Self-contained styling when possible
- Clear prop interfaces
- Comprehensive documentation

## Naming Convention

Component files use PascalCase:
- `Button.jsx`
- `ChatInterface.jsx`
- `DocumentUploader.jsx`

## Composition

Complex components should be composed of simpler ones:
- Break down large components into smaller parts
- Export composite components as default
- Export child components as named exports when appropriate

## Styling

Components use CSS modules or styled-components for scoped styling:
- Styles are colocated with components
- Class names follow BEM methodology
- Theme variables are centralized