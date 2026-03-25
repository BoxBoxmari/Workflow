# Full-Stack Developer – Reference (Code Examples)

Full code examples for the fullstack-developer skill. Use when implementing features end-to-end.

---

## 1. Shared Type Definitions (types/api.ts)

```typescript
export interface User {
  id: string;
  email: string;
  name: string;
  role: 'admin' | 'user';
  createdAt: string;
  updatedAt: string;
}

export interface CreateUserRequest {
  email: string;
  name: string;
  password: string;
}

export interface LoginRequest {
  email: string;
  password: string;
}

export interface AuthResponse {
  user: User;
  token: string;
  refreshToken: string;
}

export interface ApiResponse<T> {
  success: boolean;
  data?: T;
  error?: string;
  message?: string;
}

export interface PaginatedResponse<T> {
  data: T[];
  pagination: {
    page: number;
    limit: number;
    total: number;
    totalPages: number;
  };
}

export interface CreatePostRequest {
  title: string;
  content: string;
  tags: string[];
  published: boolean;
}

export interface Post {
  id: string;
  title: string;
  content: string;
  slug: string;
  tags: string[];
  published: boolean;
  authorId: string;
  author: User;
  createdAt: string;
  updatedAt: string;
  viewCount: number;
  likeCount: number;
}
```

---

## 2. Backend API (Express)

- **app.ts**: helmet, cors, rate-limit, compression, express.json, routes under `/api/auth`, `/api/users`, `/api/posts`, errorHandler, GET `/health`, 404 handler.
- **auth routes**: register (zod validation, bcrypt hash, JWT + refresh token), login (compare password, return tokens), refresh (verify refresh token, return new access token). Use `validateRequest(schema)` middleware.

---

## 3. Database Models (Mongoose)

- **User**: email (unique, index), name, password, role enum, emailVerified, lastLogin, timestamps; toJSON omit password; indexes email, role, createdAt.
- **Post**: title, content, slug (unique), tags[], published, authorId (ref User), viewCount, likeCount, timestamps; compound indexes (published, createdAt), (authorId, published), (tags, published), text(title, content); virtual `author` for populate.

---

## 4. Frontend App (React)

- **App.tsx**: QueryClient with retry/cache options; ErrorBoundary > QueryClientProvider > AuthProvider > Router > Layout > Routes (public + ProtectedRoute for /dashboard, /posts/create, /profile); Toaster, ReactQueryDevtools.
- **AuthContext**: state (user, token, isLoading, isAuthenticated); reducer (LOGIN_START, LOGIN_SUCCESS, LOGIN_FAILURE, LOGOUT, SET_LOADING); useEffect verify token on mount; login, register, logout; useAuth() throws if outside provider.

---

## 5. API Client (Axios)

- Instance: baseURL from env, timeout 10s, JSON headers.
- Request interceptor: add `Authorization: Bearer ${token}` from localStorage.
- Response interceptor: on 401 retry with refresh token; store new token and retry; on refresh failure redirect /login; other errors toast from response or generic.
- Exports: authAPI (login, register, verifyToken), postsAPI (getPosts, getPost, createPost, updatePost, deletePost, likePost), usersAPI (getProfile, updateProfile).

---

## 6. Reusable Components

- **PostCard**: props post, showActions?, className?; useAuth, useMutation(likePost); update cache on success; Tailwind layout; link to post, tags, view/like counts, Like button.
- **LoadingSpinner**: size sm/md/lg, className.
- **ErrorBoundary**: getDerivedStateFromError, componentDidCatch; fallback UI with message and Refresh button.

---

## 7. Testing (Jest + RTL)

- Wrap with QueryClientProvider, BrowserRouter, AuthProvider.
- PostCard: render post info; like button updates cache and shows toast.
- Use mockPost, mockUser from __mocks__/data.

---

## 8. Performance (useInfiniteScroll)

- useInfiniteQuery for posts with getNextPageParam from pagination.
- Scroll listener: when near bottom and hasNextPage and !isFetchingNextPage, fetchNextPage.
- Return posts (flatMap pages), isLoading, isFetchingNextPage, hasNextPage, error.
