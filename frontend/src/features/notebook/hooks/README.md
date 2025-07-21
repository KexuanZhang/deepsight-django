# Notebook Hooks Documentation

This directory contains all custom React hooks for the notebook feature, organized by domain and functionality.

## Directory Structure

```
hooks/
├── shared/           # Shared utilities and common patterns
│   ├── useApiUtils.ts    # API utilities (CSRF, auth, requests)
│   └── useAsyncState.ts  # Generic async state management
├── data/            # Data management hooks
│   └── useNotebookData.ts
├── file/            # File handling hooks
│   ├── useFileUpload.ts
│   └── useFileSelection.ts
├── chat/            # Chat functionality hooks
│   └── useChat.ts
├── generation/      # Generation and job management hooks
│   ├── useJobStatus.ts
│   └── useGenerationState.ts
├── studio/          # Studio-specific hooks
│   └── useStudioData.ts
└── index.ts         # Main exports
```

## Hook Categories

### 🛠️ Shared Hooks (`shared/`)

**Purpose**: Common utilities and patterns used across multiple hooks

#### `useApiUtils`
- **Purpose**: Centralized API utilities and authentication
- **Features**:
  - CSRF token management
  - Authenticated HTTP methods (GET, POST, PUT, PATCH, DELETE)
  - Standardized error handling
  - Response parsing
- **Usage**: Import in any hook that needs API functionality

#### `useAsyncState<T, E>`
- **Purpose**: Generic async state management
- **Features**:
  - Loading, error, and data state management
  - Automatic state updates during async operations
  - Stale data detection
  - Success/failure callbacks
- **Usage**: Base hook for any async operation

### 📊 Data Hooks (`data/`)

**Purpose**: Notebook data management and CRUD operations

#### `useNotebookData`
- **Purpose**: Notebook CRUD operations and state management
- **Features**:
  - Fetch all notebooks with sorting
  - Create, update, delete notebooks
  - Current notebook selection
  - Error handling and loading states
- **Dependencies**: `useApiUtils`, `useAsyncState`

### 📁 File Hooks (`file/`)

**Purpose**: File upload, validation, and selection management

#### `useFileUpload`
- **Purpose**: File upload functionality and validation
- **Features**:
  - File validation (type, size, name)
  - Drag & drop handlers
  - Upload progress tracking
  - Virtual file creation
- **Dependencies**: None (pure utility)

#### `useFileSelection`
- **Purpose**: File selection state management
- **Features**:
  - Multi-file selection
  - Selection state persistence
  - Bulk operations
- **Dependencies**: None (pure state)

### 💬 Chat Hooks (`chat/`)

**Purpose**: Chat functionality and message management

#### `useChat`
- **Purpose**: Complete chat functionality
- **Features**:
  - Message sending and receiving
  - Chat history management
  - Suggested questions
  - Real-time updates
  - Message caching
- **Dependencies**: `ChatService`, `useApiUtils`

### ⚙️ Generation Hooks (`generation/`)

**Purpose**: Job management and generation status tracking

#### `useJobStatus`
- **Purpose**: Real-time job status monitoring
- **Features**:
  - Server-Sent Events (SSE) connection
  - Progress tracking
  - Auto-reconnection
  - Job completion handling
- **Dependencies**: `apiService`

#### `useGenerationState`
- **Purpose**: Generation state management
- **Features**:
  - Job state tracking
  - Progress updates
  - Error handling
- **Dependencies**: `useAsyncState`

### 🎨 Studio Hooks (`studio/`)

**Purpose**: Studio-specific functionality

#### `useStudioData`
- **Purpose**: Studio data management
- **Features**:
  - Studio configuration
  - Generation settings
  - UI state management
- **Dependencies**: `useAsyncState`

## Best Practices

### 1. **Use Shared Hooks**
Always use `useApiUtils` and `useAsyncState` instead of duplicating functionality:

```typescript
// ✅ Good
const { get, post } = useApiUtils();
const { data, loading, error, execute } = useAsyncState<Notebook[]>();

// ❌ Bad
const [loading, setLoading] = useState(false);
const [error, setError] = useState(null);
const getCookie = useCallback((name) => { /* ... */ }, []);
```

### 2. **Comprehensive Documentation**
Each hook should have:
- Purpose description
- Feature list
- Usage examples
- Dependencies
- Return type documentation

### 3. **Type Safety**
- Use TypeScript generics for flexible typing
- Define proper interfaces for all data structures
- Use strict typing for API responses

### 4. **Error Handling**
- Use the shared error handling from `useApiUtils`
- Provide meaningful error messages
- Handle network failures gracefully

### 5. **Performance**
- Use `useCallback` for expensive operations
- Implement proper cleanup in `useEffect`
- Avoid unnecessary re-renders

## Usage Examples

### Basic Hook Usage
```typescript
import { useNotebookData } from '@/features/notebook/hooks';

const MyComponent = () => {
  const { 
    notebooks, 
    loading, 
    error, 
    fetchNotebooks 
  } = useNotebookData();

  useEffect(() => {
    fetchNotebooks();
  }, [fetchNotebooks]);

  if (loading) return <div>Loading...</div>;
  if (error) return <div>Error: {error}</div>;

  return (
    <div>
      {notebooks.map(notebook => (
        <div key={notebook.id}>{notebook.name}</div>
      ))}
    </div>
  );
};
```

### Using Shared Hooks
```typescript
import { useApiUtils, useAsyncState } from '@/features/notebook/hooks/shared';

const useCustomHook = () => {
  const { get, post } = useApiUtils();
  const { data, loading, error, execute } = useAsyncState<MyDataType>();

  const fetchData = useCallback(async () => {
    await execute(async () => {
      return await get<MyDataType>('/api/endpoint');
    });
  }, [execute, get]);

  return { data, loading, error, fetchData };
};
```

## Migration Guide

### From Old Pattern to New Pattern

**Before (Duplicated Code)**:
```typescript
const [loading, setLoading] = useState(false);
const [error, setError] = useState(null);
const getCookie = useCallback((name) => { /* ... */ }, []);

const fetchData = useCallback(async () => {
  setLoading(true);
  setError(null);
  try {
    const response = await fetch(url, {
      headers: { 'X-CSRFToken': getCookie('csrftoken') }
    });
    // ... handle response
  } catch (err) {
    setError(err.message);
  } finally {
    setLoading(false);
  }
}, [getCookie]);
```

**After (Using Shared Hooks)**:
```typescript
const { get } = useApiUtils();
const { data, loading, error, execute } = useAsyncState<DataType>();

const fetchData = useCallback(async () => {
  await execute(async () => {
    return await get<DataType>('/api/endpoint');
  });
}, [execute, get]);
```

## Testing

Each hook should have corresponding tests that cover:
- Happy path scenarios
- Error handling
- Edge cases
- State transitions
- Cleanup behavior

## Contributing

When adding new hooks:
1. Determine the appropriate category
2. Use shared hooks when possible
3. Add comprehensive documentation
4. Include TypeScript types
5. Add tests
6. Update this README if needed 