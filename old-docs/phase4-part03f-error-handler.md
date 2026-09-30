# Phase 4 — Part 03f: Global Error Handler (middleware/error_handler.py)

| Field | Value |
|-------|-------|
| **Part** | 03f |
| **File** | `backend/app/middleware/error_handler.py` |
| **Next** | [Part 03g — logging_middleware.py](./phase4-part03g-logging-middleware.md) |
| **Difficulty** | 🟡 Medium |
| **Time to Type** | ~12 minutes |
| **Lines** | ~80 lines |

---

## What Does the Error Handler Do? Read This First

Without a global error handler, unhandled exceptions return ugly HTML:

```html
<html><body><h1>500 Internal Server Error</h1></body></html>
```

Your React frontend expects JSON. The error handler ensures EVERY error — handled or unhandled — returns consistent JSON:

```json
{"error_code": "HABIT_NOT_FOUND", "message": "Habit not found", "detail": null}
```

It has 4 handler functions:
1. **`BaseAppError`** → our custom errors (404, 409, 422, 401, 403) → log as `warning`
2. **`RequestValidationError`** → Pydantic validation failures (422) → log as `warning`
3. **`StarletteHTTPException`** → framework errors (405, 404 for unknown routes) → pass through
4. **`Exception`** → anything unexpected (500) → log as `error` with traceback, return generic message (NEVER expose internals)

---

## Source Code

> 📁 **File:** `backend/app/middleware/error_handler.py`
> Type the full code from the source file

**Critical security line:**
```python
# NEVER expose the actual error message to the user in production.
# It might contain: SQL queries, file paths, API keys.
return JSONResponse(
    status_code=500,
    content={"error_code": "INTERNAL_ERROR", "message": "An unexpected error occurred."}
)
```

---

## 🎤 Interview Q&A

### Q: "How do you handle unhandled exceptions?"

> "A global exception handler registered on the FastAPI app. It catches 4 types: our custom `BaseAppError` subclasses (returns the error's status code and message), Pydantic `RequestValidationError` (422 with field-level details), Starlette HTTP exceptions (pass through), and the catch-all `Exception` (always returns 500 with a generic message — NEVER expose internal error details in production because they might contain SQL queries or file paths). Every error returns the same JSON structure: `{error_code, message, detail}`."

---

| ← Previous | [📚 Index](./INDEX.md) | Next → |
|:-----------|:---------------------:|-------:|
| [Part 03e](./phase4-part03e-logging.md) | | [Part 03g — logging_middleware.py](./phase4-part03g-logging-middleware.md) |
