# Source Code

This directory contains all frontend source code.

## Structure

```
src/
├── components/       # Reusable UI components
├── pages/            # Page-level components
├── services/         # API service layer
├── hooks/            # Custom React hooks
├── utils/            # Utility functions
├── App.jsx           # Main App component
├── main.jsx          # Application entry point
└── README.md         # This file
```

## Entry Point

`main.jsx` is the application entry point that:
- Renders the main App component
- Sets up React rendering
- Initializes global providers (if any)

## Main Component

`App.jsx` contains the main application structure:
- Router configuration
- Layout components
- Global state providers

## Module Organization

Source code is organized by functionality:
- **Components**: Reusable UI elements
- **Pages**: Full-page views that compose components
- **Services**: API interaction layer
- **Hooks**: Custom React hooks for state and logic
- **Utils**: Helper functions