# 🧪 Phase 5 Part 02: Unit Tests

> **"Four unit test files testing pure logic with zero external dependencies: bcrypt hashing + JWT tokens (11 tests), date utilities (12 tests), RAG text chunking (7 tests), and the ReAct agent loop with mocked LLM (5 agent + 3 memory tests). All run in ~2 seconds."**

---

## 📋 Document Metadata

| Field | Value |
|-------|-------|
| **Previous** | [phase5-part01-testing-overview-infrastructure.md](./phase5-part01-testing-overview-infrastructure.md) |
| **Next** | [phase5-part03-integration-tests.md](./phase5-part03-integration-tests.md) |
| **Files in This Doc** | 4 unit test files |
| **Time to Type** | ~40 minutes |
| **Difficulty** | Easy-Medium (no DB, no HTTP — just assert on return values) |

---

## 1. `tests/unit/test_auth_security.py` — JWT + Password Hashing

### Type This Code:

```python
# ============================================================================
# Unit Tests — Auth Security (JWT + Password Hashing)
# ============================================================================
# Tests the core security functions WITHOUT a database.
# These are pure functions — hash, verify, create token, decode token.
# ============================================================================

import pytest
from uuid import uuid4

from app.modules.auth.security import (
    hash_password,
    verify_password,
    create_access_token,
    create_refresh_token,
    decode_token,
)
from app.modules.auth.exceptions import TokenExpiredError, TokenInvalidError


class TestPasswordHashing:
    """Test bcrypt password hashing and verification."""

    def test_hash_password_returns_hash(self):
        """Hashing a password returns a bcrypt hash string."""
        hashed = hash_password("mySecurePass123")
        assert hashed != "mySecurePass123"  # Not plain text
        assert hashed.startswith("$2b$")    # Bcrypt prefix
        assert len(hashed) > 50             # Bcrypt hashes are ~60 chars

    def test_verify_correct_password(self):
        """Correct password verifies against its hash."""
        hashed = hash_password("mySecurePass123")
        assert verify_password("mySecurePass123", hashed) is True

    def test_verify_wrong_password(self):
        """Wrong password does NOT verify."""
        hashed = hash_password("mySecurePass123")
        assert verify_password("wrongPassword", hashed) is False

    def test_different_hashes_for_same_password(self):
        """Same password produces different hashes (random salt)."""
        hash1 = hash_password("samePassword")
        hash2 = hash_password("samePassword")
        assert hash1 != hash2  # Different salts → different hashes
        # But both verify correctly
        assert verify_password("samePassword", hash1) is True
        assert verify_password("samePassword", hash2) is True


class TestJWTTokens:
    """Test JWT token creation and decoding."""

    def test_create_access_token(self):
        """Access token is a non-empty string."""
        user_id = uuid4()
        token = create_access_token(user_id)
        assert isinstance(token, str)
        assert len(token) > 50  # JWTs are long
        assert token.count(".") == 2  # JWTs have 3 parts separated by dots

    def test_decode_valid_access_token(self):
        """Decoding a valid access token returns the payload."""
        user_id = uuid4()
        token = create_access_token(user_id)
        payload = decode_token(token, expected_type="access")

        assert payload["sub"] == str(user_id)
        assert payload["type"] == "access"
        assert "exp" in payload
        assert "iat" in payload

    def test_create_refresh_token(self):
        """Refresh token is created and decodable."""
        user_id = uuid4()
        token = create_refresh_token(user_id)
        payload = decode_token(token, expected_type="refresh")

        assert payload["sub"] == str(user_id)
        assert payload["type"] == "refresh"

    def test_decode_wrong_type_raises_error(self):
        """Using a refresh token as access token raises TokenInvalidError."""
        user_id = uuid4()
        refresh_token = create_refresh_token(user_id)

        with pytest.raises(TokenInvalidError):
            decode_token(refresh_token, expected_type="access")

    def test_decode_garbage_token_raises_error(self):
        """Decoding a garbage string raises TokenInvalidError."""
        with pytest.raises(TokenInvalidError):
            decode_token("not.a.valid.jwt.token", expected_type="access")

    def test_decode_empty_token_raises_error(self):
        """Decoding an empty string raises TokenInvalidError."""
        with pytest.raises(TokenInvalidError):
            decode_token("", expected_type="access")

    def test_different_users_get_different_tokens(self):
        """Different user IDs produce different tokens."""
        token1 = create_access_token(uuid4())
        token2 = create_access_token(uuid4())
        assert token1 != token2
```

### Key Testing Patterns

**`pytest.raises(TokenInvalidError)`** — Context manager that asserts an exception is raised. If `decode_token` does NOT raise `TokenInvalidError`, the test FAILS. This is how you test error paths.

**`assert hashed.startswith("$2b$")`** — Verifies the bcrypt format without caring about the exact value. Bcrypt hashes always start with `$2b$` (the algorithm identifier).

**`test_different_hashes_for_same_password`** — This test catches a common security bug: if two users have the same password, their hashes should be different (because bcrypt uses a random salt). Without salt, rainbow table attacks work.

---

## 2. `tests/unit/test_date_utils.py` — Date Utilities

### Type This Code:

```python
# ============================================================================
# Unit Tests — Date Utilities
# ============================================================================

from datetime import date, datetime, timezone

from app.shared.date_utils import (
    utc_now,
    today_utc,
    to_user_timezone,
    start_of_week,
    end_of_week,
    start_of_month,
    end_of_month,
    date_range,
    days_ago,
)


class TestUtcNow:
    def test_returns_timezone_aware(self):
        now = utc_now()
        assert now.tzinfo is not None
        assert now.tzinfo == timezone.utc

    def test_returns_datetime(self):
        assert isinstance(utc_now(), datetime)


class TestTodayUtc:
    def test_returns_date(self):
        assert isinstance(today_utc(), date)


class TestToUserTimezone:
    def test_convert_utc_to_india(self):
        utc_time = datetime(2026, 9, 26, 18, 30, tzinfo=timezone.utc)
        local = to_user_timezone(utc_time, "Asia/Kolkata")
        # IST is UTC+5:30 → 18:30 UTC = 00:00 IST (next day)
        assert local.hour == 0
        assert local.day == 27

    def test_convert_utc_to_new_york(self):
        utc_time = datetime(2026, 9, 26, 12, 0, tzinfo=timezone.utc)
        local = to_user_timezone(utc_time, "America/New_York")
        # EDT is UTC-4 → 12:00 UTC = 08:00 EDT
        assert local.hour == 8


class TestStartOfWeek:
    def test_monday_is_start(self):
        # September 26, 2026 is a Saturday
        result = start_of_week(date(2026, 9, 26))
        assert result == date(2026, 9, 21)  # Monday
        assert result.weekday() == 0  # 0 = Monday

    def test_monday_returns_itself(self):
        monday = date(2026, 9, 21)
        assert start_of_week(monday) == monday


class TestEndOfWeek:
    def test_sunday_is_end(self):
        result = end_of_week(date(2026, 9, 26))
        assert result == date(2026, 9, 27)  # Sunday
        assert result.weekday() == 6  # 6 = Sunday


class TestStartOfMonth:
    def test_returns_first_day(self):
        assert start_of_month(date(2026, 9, 26)) == date(2026, 9, 1)

    def test_first_day_returns_itself(self):
        assert start_of_month(date(2026, 9, 1)) == date(2026, 9, 1)


class TestEndOfMonth:
    def test_september_has_30_days(self):
        assert end_of_month(date(2026, 9, 15)) == date(2026, 9, 30)

    def test_february_non_leap(self):
        assert end_of_month(date(2025, 2, 10)) == date(2025, 2, 28)

    def test_december(self):
        assert end_of_month(date(2026, 12, 5)) == date(2026, 12, 31)


class TestDateRange:
    def test_generates_inclusive_range(self):
        result = date_range(date(2026, 9, 1), date(2026, 9, 5))
        assert len(result) == 5
        assert result[0] == date(2026, 9, 1)
        assert result[-1] == date(2026, 9, 5)

    def test_single_day_range(self):
        result = date_range(date(2026, 9, 1), date(2026, 9, 1))
        assert len(result) == 1


class TestDaysAgo:
    def test_zero_days_ago_is_today(self):
        assert days_ago(0) == today_utc()

    def test_seven_days_ago(self):
        result = days_ago(7)
        assert (today_utc() - result).days == 7
```

**Edge case coverage:** `test_february_non_leap` catches bugs where someone hardcodes 28/30/31 instead of calculating the actual month length. `test_monday_returns_itself` catches off-by-one errors in the start-of-week calculation.

---

## 3. `tests/unit/test_rag_chunker.py` — RAG Text Chunking

### Type This Code:

```python
# ============================================================================
# Unit Tests — RAG Text Chunker
# ============================================================================

import pytest
from app.modules.ai.rag.chunker import TextChunker


class TestTextChunker:
    """Test the recursive text chunking algorithm."""

    def setup_method(self):
        self.chunker = TextChunker(chunk_size=200, chunk_overlap=20, min_chunk_size=10)

    def test_short_text_single_chunk(self):
        """Text shorter than chunk_size returns one chunk."""
        chunks = self.chunker.chunk_text("This is a short text.")
        assert len(chunks) == 1
        assert chunks[0].text == "This is a short text."
        assert chunks[0].index == 0

    def test_empty_text_no_chunks(self):
        """Empty text returns no chunks."""
        assert self.chunker.chunk_text("") == []
        assert self.chunker.chunk_text("   ") == []

    def test_long_text_multiple_chunks(self):
        """Long text is split into multiple chunks."""
        text = "This is a paragraph about health. " * 20
        chunks = self.chunker.chunk_text(text)
        assert len(chunks) >= 2
        for chunk in chunks:
            assert len(chunk.text) >= self.chunker.min_chunk_size

    def test_chunk_index_is_sequential(self):
        """Chunk indices are sequential starting from 0."""
        text = "Word " * 200
        chunks = self.chunker.chunk_text(text)
        for i, chunk in enumerate(chunks):
            assert chunk.index == i

    def test_paragraphs_split_at_boundaries(self):
        """Text with paragraphs splits at paragraph boundaries."""
        text = ("First paragraph content here.\n\n"
                "Second paragraph content here.\n\n"
                "Third paragraph content here.")
        chunker = TextChunker(chunk_size=60, chunk_overlap=5, min_chunk_size=10)
        chunks = chunker.chunk_text(text)
        assert len(chunks) >= 2

    def test_page_tracking(self):
        """Chunks track which page they came from."""
        page_texts = [
            "Page one content goes here with enough text.",
            "Page two has different content about health.",
        ]
        text = "\n\n".join(page_texts)
        chunker = TextChunker(chunk_size=500, chunk_overlap=20, min_chunk_size=10)
        chunks = chunker.chunk_text(text, page_texts=page_texts)
        if chunks:
            assert chunks[0].page_number is not None

    def test_token_count_estimation(self):
        """Token count is approximately text_length / 4."""
        text = "a" * 400  # 400 chars ≈ 100 tokens
        chunker = TextChunker(chunk_size=500, chunk_overlap=0, min_chunk_size=10)
        chunks = chunker.chunk_text(text)
        assert len(chunks) == 1
        assert chunks[0].token_count == 100  # 400 / 4
```

**`setup_method(self)`** — Called before each test in the class. Creates a fresh `TextChunker` with test-friendly settings (small chunk size so we don't need huge text inputs).

---

## 4. `tests/unit/test_ai_agent.py` — ReAct Agent Loop

### Type This Code:

```python
# ============================================================================
# Unit Tests — AI ReAct Agent
# ============================================================================
# Tests the agent loop with a mocked LLM — no real API calls.
# ============================================================================

import pytest
from app.modules.ai.agents.base_agent import BaseAgent
from app.modules.ai.agents.memory.short_term import ShortTermMemory
from app.modules.ai.agents.tools.base_tool import BaseTool
from app.modules.ai.llm.base_client import LLMResponse, ToolCall
from tests.mocks.mock_llm_client import MockLLMClient


# ── Fake Tool for Testing ──
class FakeCalculatorTool(BaseTool):
    @property
    def name(self) -> str:
        return "calculator"

    @property
    def description(self) -> str:
        return "Calculates a math expression"

    @property
    def parameters_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {"expression": {"type": "string"}},
            "required": ["expression"],
        }

    async def execute(self, **kwargs) -> str:
        return "Result: 42"


class TestBaseAgent:
    """Test the ReAct agent loop."""

    @pytest.mark.asyncio
    async def test_direct_response_no_tools(self):
        """Agent returns text response when no tool calls are made."""
        llm = MockLLMClient(response_text="Your sleep averaged 7 hours this week.")
        agent = BaseAgent(llm=llm, tools=[], system_prompt="You are a test agent.")

        result = await agent.run("How's my sleep?")

        assert "7 hours" in result
        assert llm.call_count == 1

    @pytest.mark.asyncio
    async def test_agent_calls_tool_then_responds(self):
        """Agent calls a tool, gets the result, then generates a final response."""
        tool_call = ToolCall(name="calculator", arguments={"expression": "6 * 7"})
        llm = MockLLMClient(
            response_text="The answer is 42, based on the calculation.",
            tool_calls=[tool_call],
        )
        tool = FakeCalculatorTool()
        agent = BaseAgent(llm=llm, tools=[tool], system_prompt="You are a test agent.")

        result = await agent.run("What is 6 times 7?")

        assert "42" in result
        assert llm.call_count == 2  # Tool call + final response

    @pytest.mark.asyncio
    async def test_agent_respects_max_iterations(self):
        """Agent stops after max_iterations even if LLM keeps requesting tools."""
        tool_call = ToolCall(name="calculator", arguments={"expression": "1+1"})
        llm = MockLLMClient(response_text="Final answer.", tool_calls=[tool_call])

        async def always_tool_call(*args, **kwargs):
            return LLMResponse(
                content="", tool_calls=[tool_call],
                input_tokens=10, output_tokens=10, model="mock",
            )
        llm.chat = always_tool_call  # type: ignore

        tool = FakeCalculatorTool()
        agent = BaseAgent(
            llm=llm, tools=[tool], system_prompt="Test", max_iterations=3,
        )

        result = await agent.run("Keep calculating forever")
        assert isinstance(result, str)

    @pytest.mark.asyncio
    async def test_memory_stores_conversation(self):
        """Agent's memory stores user message and assistant response."""
        memory = ShortTermMemory(max_messages=20)
        llm = MockLLMClient(response_text="You're doing great!")
        agent = BaseAgent(llm=llm, tools=[], system_prompt="Test", memory=memory)

        await agent.run("How am I doing?")

        messages = memory.get_messages()
        assert len(messages) >= 2
        assert messages[0].role == "user"
        assert messages[0].content == "How am I doing?"
        assert messages[1].role == "assistant"
        assert "doing great" in messages[1].content

    @pytest.mark.asyncio
    async def test_unknown_tool_handled_gracefully(self):
        """Agent handles LLM requesting a tool that doesn't exist."""
        tool_call = ToolCall(name="nonexistent_tool", arguments={})
        llm = MockLLMClient(
            response_text="Sorry, I had trouble.", tool_calls=[tool_call],
        )
        agent = BaseAgent(llm=llm, tools=[], system_prompt="Test")

        result = await agent.run("Do something")
        assert isinstance(result, str)  # Should not crash


class TestShortTermMemory:
    """Test the conversation buffer."""

    def test_add_and_retrieve(self):
        memory = ShortTermMemory(max_messages=10)
        memory.add_user_message("Hello")
        memory.add_assistant_message("Hi there!")

        messages = memory.get_messages()
        assert len(messages) == 2
        assert messages[0].role == "user"
        assert messages[1].role == "assistant"

    def test_sliding_window(self):
        """Old messages are dropped when buffer is full."""
        memory = ShortTermMemory(max_messages=3)
        memory.add_user_message("msg1")
        memory.add_assistant_message("msg2")
        memory.add_user_message("msg3")
        memory.add_assistant_message("msg4")  # Pushes msg1 out

        messages = memory.get_messages()
        assert len(messages) == 3
        assert messages[0].content == "msg2"  # msg1 was dropped

    def test_clear(self):
        memory = ShortTermMemory()
        memory.add_user_message("Hello")
        memory.clear()
        assert memory.get_message_count() == 0
```

### How MockLLMClient Simulates the ReAct Loop

```
test_agent_calls_tool_then_responds:

  agent.run("What is 6 times 7?")
    │
    ├─ LLM call #1 (MockLLMClient):
    │   self.call_count == 1 AND self.tool_calls is non-empty
    │   → Returns: LLMResponse(content="", tool_calls=[calculator("6 * 7")])
    │
    ├─ Agent executes tool: FakeCalculatorTool.execute() → "Result: 42"
    │
    ├─ LLM call #2 (MockLLMClient):
    │   self.call_count == 2 → tool_calls check skipped
    │   → Returns: LLMResponse(content="The answer is 42, based on the calculation.")
    │
    └─ Agent returns: "The answer is 42, based on the calculation."

  assert "42" in result  ✅
  assert llm.call_count == 2  ✅
```

---

## 5. What You Learned

| # | Concept | Where |
|---|---------|-------|
| 1 | **`pytest.raises()`** | test_auth — assert exceptions are raised |
| 2 | **`setup_method()`** | test_rag_chunker — per-test setup |
| 3 | **`@pytest.mark.asyncio`** | test_ai_agent — async test functions |
| 4 | **Fake tool class** | FakeCalculatorTool — test agent without real tools |
| 5 | **`llm.call_count`** | Verify how many LLM calls the agent made |
| 6 | **Edge case tests** | February, empty strings, garbage tokens |
| 7 | **Sliding window test** | ShortTermMemory — verify oldest messages dropped |
| 8 | **Class-based test organization** | Group related tests in classes |

---

## 6. Navigation

| Direction | Document |
|-----------|----------|
| ⬅️ Previous | [Phase 5 Part 01: Testing Infrastructure](./phase5-part01-testing-overview-infrastructure.md) |
| ➡️ Next | [Phase 5 Part 03: Integration Tests](./phase5-part03-integration-tests.md) |

---

**End of Phase 5 Part 02: Unit Tests**
