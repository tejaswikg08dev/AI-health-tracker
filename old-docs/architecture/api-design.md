# API Design — Health Tracker

## Conventions

| Convention | Rule | Example |
|-----------|------|---------|
| Base URL | `/api/v1/{module}` | `/api/v1/habits` |
| Versioning | URL prefix `/v1/` | Breaking changes → `/v2/` |
| Naming | Plural nouns, kebab-case for multi-word | `/habit-logs`, `/weekly-summary` |
| Methods | GET (read), POST (create), PUT (update), DELETE (remove) | `PUT /habits/:id` |
| Status codes | 200 (OK), 201 (created), 401 (unauth), 404 (not found), 422 (validation), 429 (rate limit) | |
| Auth | Bearer token in Authorization header | `Authorization: Bearer eyJ...` |
| Errors | Consistent JSON: `{error_code, message, detail}` | `{"error_code": "HABIT_NOT_FOUND", "message": "..."}` |
| Dates | ISO 8601 strings | `"2026-09-26"`, `"2026-09-26T10:00:00Z"` |
| IDs | UUID v4 strings | `"550e8400-e29b-41d4-a716-446655440000"` |

## Complete Endpoint Reference (38 endpoints)

### Auth (`/api/v1/auth`)
| Method | Path | Description | Auth |
|--------|------|-------------|------|
| POST | `/signup` | Register new user | No |
| POST | `/login` | Get JWT tokens | No |
| POST | `/refresh` | Refresh expired token | No |
| POST | `/logout` | Blacklist token | Yes |
| GET | `/me` | Get profile | Yes |
| PUT | `/me` | Update profile | Yes |

### Habits (`/api/v1/habits`)
| Method | Path | Description | Auth |
|--------|------|-------------|------|
| POST | `/` | Create habit | Yes |
| GET | `/` | List habits | Yes |
| GET | `/:id` | Get single habit | Yes |
| PUT | `/:id` | Update habit | Yes |
| DELETE | `/:id` | Archive habit | Yes |
| PUT | `/reorder` | Reorder habits | Yes |

### Logs (`/api/v1/logs`)
| Method | Path | Description | Auth |
|--------|------|-------------|------|
| POST | `/` | Create single log | Yes |
| POST | `/bulk` | Bulk create/update | Yes |
| GET | `/` | Get logs (date/range) | Yes |
| PUT | `/:id` | Update log | Yes |
| DELETE | `/:id` | Delete log | Yes |

### Analytics (`/api/v1/analytics`)
| Method | Path | Description | Auth |
|--------|------|-------------|------|
| GET | `/dashboard` | Dashboard overview | Yes |
| GET | `/streaks` | All habit streaks | Yes |
| GET | `/weekly-summary` | This vs last week | Yes |
| GET | `/monthly-trend` | 30-day chart data | Yes |
| GET | `/completion-rate` | Completion % per habit | Yes |
| GET | `/correlations` | Habit correlations | Yes |

### AI (`/api/v1/ai`)
| Method | Path | Description | Auth |
|--------|------|-------------|------|
| POST | `/chat` | Chat with AI | Yes |
| GET | `/chat/stream` | SSE streaming chat | Yes |
| GET | `/chat/history` | Chat history | Yes |
| POST | `/documents` | Upload document (RAG) | Yes |
| GET | `/documents` | List documents | Yes |
| DELETE | `/documents/:id` | Delete document | Yes |
| POST | `/insights` | Generate insight | Yes |
| GET | `/insights` | List insights | Yes |
| POST | `/weekly-report` | Generate report | Yes |

### Notifications (`/api/v1/notifications`)
| Method | Path | Description | Auth |
|--------|------|-------------|------|
| GET | `/settings` | Get preferences | Yes |
| PUT | `/settings` | Update preferences | Yes |
| POST | `/test-email` | Send test email | Yes |

### Export (`/api/v1/export`)
| Method | Path | Description | Auth |
|--------|------|-------------|------|
| POST | `/csv` | Download CSV | Yes |
| POST | `/csv/s3` | Export to S3 + URL | Yes |

### Health
| Method | Path | Description | Auth |
|--------|------|-------------|------|
| GET | `/health` | Health check | No |

## Error Response Format

Every error follows this structure:
```json
{
    "error_code": "HABIT_NOT_FOUND",
    "message": "Habit not found",
    "detail": null
}
```

Common error codes:
| Code | HTTP | Meaning |
|------|------|---------|
| `INVALID_CREDENTIALS` | 401 | Wrong email or password |
| `TOKEN_EXPIRED` | 401 | JWT expired, use refresh |
| `TOKEN_INVALID` | 401 | Malformed or tampered token |
| `HABIT_NOT_FOUND` | 404 | Habit doesn't exist or wrong user |
| `EMAIL_ALREADY_EXISTS` | 409 | Duplicate email on signup |
| `DUPLICATE_LOG` | 409 | Log already exists for habit+date |
| `VALIDATION_ERROR` | 422 | Request body validation failed |
| `FUTURE_DATE` | 422 | Cannot log for future dates |
| `RATE_LIMIT_EXCEEDED` | 429 | Too many requests |
