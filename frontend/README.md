# Frontend - React Application

This directory contains the frontend application built with React.

## Structure

```
frontend/
├── public/           # Public assets
├── src/              # Source code
├── Dockerfile        # Docker configuration
├── package.json      # NPM dependencies and scripts
└── README.md         # This file
```

## Main Components

- `src/App.jsx`: Main application component
- `src/components/`: Reusable UI components
- `src/pages/`: Page-level components
- `src/services/`: API service layer
- `src/hooks/`: Custom React hooks
- `src/utils/`: Utility functions

## Development

To run the frontend locally for development:

```bash
# Install dependencies
npm install

# Run development server
npm run dev
```

## Build for Production

To build the application for production:

```bash
npm run build
```

This creates an optimized build in the `dist/` directory.

## Preview Production Build

To preview the production build locally:

```bash
npm run preview
```

## Dependencies

Main dependencies include:
- React: UI library
- React Router: Client-side routing
- Axios: HTTP client for API requests