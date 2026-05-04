# Pages

This directory contains page-level components that represent complete views.

## Structure

```
pages/
├── Home.jsx          # Homepage
├── Chat.jsx          # Chat interface page
├── Documents.jsx     # Document management page
└── README.md         # This file
```

## Page Responsibilities

Each page component:
- Represents a complete view or screen
- Composes multiple smaller components
- Manages local state for the view
- Handles routing parameters
- Integrates with API services

## Routing

Pages are mapped to routes in the main App component:
- `/` -> Home page
- `/chat` -> Chat page
- `/documents` -> Documents page

## Data Flow

Pages typically:
1. Load initial data in useEffect
2. Manage loading and error states
3. Pass data to child components
4. Handle user interactions and form submissions
5. Update global state when necessary

## Code Splitting

Large pages can be code-split for performance:
- Use dynamic imports for heavy components
- Implement lazy loading where appropriate
- Show loading indicators during data fetching