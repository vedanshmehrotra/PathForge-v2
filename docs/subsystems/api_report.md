# PathForge API Layer — Report

## Architecture

The API layer is a thin FastAPI orchestration layer that exposes the five
frozen backend engines as structured HTTP endpoints.

```
Client → FastAPI Routes → Service Orchestrators → Backend Engines
                                                         │
                                                    SQLite DB
```

## Endpoints

### POST /analyze

**Input:** user_id, code, language  
**Output:** ast, match_result

Orchestrates:
1. `ASTAnalysisEngine.analyze(code)` → detected patterns
2. `MatchingEngine.match(ast, ast)` → self-match result (no LLM input available)
3. Returns both results

Errors: syntax errors → stage=AST, unsupported language → stage=VALIDATION

### POST /gaps

**Input:** user_id  
**Output:** gap_signals, summary

Orchestrates:
1. Loads `gap_signals` table for the user
2. Classifies into strong/moderate/weak gaps
3. Returns stored signals

Errors: user not found

### POST /elo

**Input:** user_id  
**Output:** pattern_elo, summary

Orchestrates:
1. Loads `user_pattern_elo` table for the user
2. Computes average Elo, weakest/strongest patterns
3. Returns stored ratings

Errors: user not found

### POST /recommend

**Input:** user_id  
**Output:** recommended_problems, summary

Orchestrates:
1. Loads problem bank, user Elo, gap signals, submissions from DB
2. Instantiates `RecommendationEngine` with problem bank
3. Calls `engine.recommend()` with all loaded data
4. Returns ranked recommendations

Errors: user not found, no problems in bank

## File Structure

```
pathforge/api/
├── __init__.py
├── app.py                    # FastAPI app creation
├── routes/
│   ├── __init__.py
│   ├── analyze.py            # POST /analyze route
│   ├── gaps.py               # POST /gaps route
│   ├── elo_route.py          # POST /elo route
│   └── recommend.py          # POST /recommend route
├── services/
│   ├── __init__.py
│   ├── analysis.py           # Calls AST + Matching Engine
│   ├── gap.py                # Loads gap signals from DB
│   ├── elo.py                # Loads Elo ratings from DB
│   ├── recommend_service.py  # Runs Recommendation Engine
│   └── loader.py             # Common DB loading functions
```

## Design Principles

1. **Thin orchestration only** — routes call services, services call engines.
   No business logic in the API layer.

2. **Stateless** — each request loads fresh data from DB. No in-memory caching
   in the API layer (can be added later via middleware).

3. **Structured errors** — all errors return `{error, stage}` to identify where
   in the pipeline the failure occurred.

4. **Pydantic validation** — request bodies validated automatically by FastAPI.
   Missing fields return 422 with field-level details.

5. **Existing engine reuse** — all backend engines are imported and used directly.
   No wrappers, no monkey-patching, no reimplementation.

## Edge Cases Handled

| Case | Behavior |
|------|----------|
| Empty code | Returns AST with zero detections |
| Syntax error | Returns 400 with stage=AST |
| Unsupported language | Returns 400 with stage=VALIDATION |
| Nonexistent user | Returns 400 with stage-specific error |
| Missing DB tables | Returns 400 with DB error detail |
| Invalid request body | FastAPI returns 422 validation error |
| No submissions yet | Returns empty/message for gaps/elo/recommend |

## Test Coverage

16 integration tests covering:
- Health check
- Input validation (missing fields, wrong types)
- Error states (syntax error, unsupported language, invalid user)
- Successful analysis of valid Python code
- All endpoint response codes

## Limitations

- `/analyze` performs self-match since no LLM expected patterns are provided
- Services open a new DB connection per request (no connection pooling)
- No authentication/authorization layer (uses FastAPI defaults)
- No rate limiting or request throttling
- No response caching

## Future Improvements

- Add connection pooling via SQLAlchemy or similar
- Add JWT authentication middleware
- Add OpenAPI response model documentation
- Add request logging middleware
- Add response caching for /gaps and /elo (slow-changing data)
- Support batch /analyze for multiple code snippets
