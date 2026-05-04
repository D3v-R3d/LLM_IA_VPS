# Custom Hooks

This directory contains custom React hooks for encapsulating reusable logic.

## Structure

```
hooks/
├── useAuth.js        # Authentication state management
├── useChat.js        # Chat-related state and logic
├── useDocuments.js   # Document management logic
├── useApi.js         # Generic API calling hook
└── README.md         # This file
```

## Hook Guidelines

Custom hooks should follow these guidelines:
- Start with "use" prefix
- Encapsulate reusable logic
- Be composable with other hooks
- Have clear, descriptive names
- Include TypeScript types where applicable
- Provide comprehensive documentation

## Best Practices

When creating hooks:
- Keep them focused on a single responsibility
- Return consistent interface patterns
- Handle cleanup in useEffect appropriately
- Memoize expensive computations
- Provide loading and error states where relevant

## Usage

Hooks are imported and used in components:

```javascript
import useAuth from '../hooks/useAuth';
import useChat from '../hooks/useChat';

function ChatComponent() {
  const { user } = useAuth();
  const { messages, sendMessage } = useChat();
  
  // Component implementation
}
```

## Testing

Each hook should have corresponding unit tests in the `__tests__` directory.