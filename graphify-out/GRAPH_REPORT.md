# Graph Report - C:\Users\pc\Desktop\FitZone Chatbot  (2026-06-28)

## Corpus Check
- 96 files · ~261,383 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 742 nodes · 1628 edges · 40 communities (34 shown, 6 thin omitted)
- Extraction: 89% EXTRACTED · 11% INFERRED · 0% AMBIGUOUS · INFERRED: 172 edges (avg confidence: 0.53)
- Token cost: 5,307 input · 5,104 output

## Community Hubs (Navigation)
- [[_COMMUNITY_Adaptive Planning & Recommendations|Adaptive Planning & Recommendations]]
- [[_COMMUNITY_API & Request Handling|API & Request Handling]]
- [[_COMMUNITY_Exercise Retrieval|Exercise Retrieval]]
- [[_COMMUNITY_Nutrition Retrieval|Nutrition Retrieval]]
- [[_COMMUNITY_Progression & 1RM Computation|Progression & 1RM Computation]]
- [[_COMMUNITY_PubMed Research Client|PubMed Research Client]]
- [[_COMMUNITY_Build & Knowledge Pipeline|Build & Knowledge Pipeline]]
- [[_COMMUNITY_Intent Routing & LLM Setup|Intent Routing & LLM Setup]]
- [[_COMMUNITY_Formula Calculator|Formula Calculator]]
- [[_COMMUNITY_Nutrition Data Ingestion|Nutrition Data Ingestion]]
- [[_COMMUNITY_Lift Log Parsing|Lift Log Parsing]]
- [[_COMMUNITY_Session Store|Session Store]]
- [[_COMMUNITY_Configuration & Logging|Configuration & Logging]]
- [[_COMMUNITY_Personality Modes|Personality Modes]]
- [[_COMMUNITY_Formula Registry|Formula Registry]]
- [[_COMMUNITY_Open Food Facts Client|Open Food Facts Client]]
- [[_COMMUNITY_Agent Core|Agent Core]]
- [[_COMMUNITY_Safety Guardrails|Safety Guardrails]]
- [[_COMMUNITY_Recovery Analysis|Recovery Analysis]]
- [[_COMMUNITY_Exercise Ingestion Pipeline|Exercise Ingestion Pipeline]]
- [[_COMMUNITY_Context Building & Streaming|Context Building & Streaming]]
- [[_COMMUNITY_Lift Parser Tests|Lift Parser Tests]]
- [[_COMMUNITY_Input Validation|Input Validation]]
- [[_COMMUNITY_Jeff Nippard Training Programs|Jeff Nippard Training Programs]]
- [[_COMMUNITY_WGER Exercise Import|WGER Exercise Import]]
- [[_COMMUNITY_API Tests|API Tests]]
- [[_COMMUNITY_Health Checks|Health Checks]]
- [[_COMMUNITY_Anatomy & Physiology Knowledge|Anatomy & Physiology Knowledge]]
- [[_COMMUNITY_Test Fixtures|Test Fixtures]]
- [[_COMMUNITY_Workout Session Model|Workout Session Model]]
- [[_COMMUNITY_Training Programs & Supplements|Training Programs & Supplements]]
- [[_COMMUNITY_ISSN Nutrition Position Stands|ISSN Nutrition Position Stands]]
- [[_COMMUNITY_Test Suite Init|Test Suite Init]]
- [[_COMMUNITY_ISSN Beta-Alanine|ISSN Beta-Alanine]]
- [[_COMMUNITY_ISSN Caffeine|ISSN Caffeine]]
- [[_COMMUNITY_Research Education Hub|Research Education Hub]]

## God Nodes (most connected - your core abstractions)
1. `SessionStore` - 51 edges
2. `ChatTurn` - 35 edges
3. `UserProfile` - 34 edges
4. `TestUserProfile` - 31 edges
5. `FitnessAgent` - 26 edges
6. `LiftParser` - 25 edges
7. `PubMedClient` - 24 edges
8. `TrendData` - 22 edges
9. `TestWeeklyTracker` - 22 edges
10. `KnowledgeRetriever` - 21 edges

## Surprising Connections (you probably didn't know these)
- `TestLiftParser` --uses--> `ParsedSet`  [INFERRED]
  tests/test_lift_parser.py → src/lift_parser.py
- `TestLiftParser` --uses--> `ParsedLift`  [INFERRED]
  tests/test_lift_parser.py → src/lift_parser.py
- `TestIsLiftLog` --uses--> `LiftParser`  [INFERRED]
  tests/test_lift_parser.py → src/lift_parser.py
- `TestLiftParser` --uses--> `LiftParser`  [INFERRED]
  tests/test_lift_parser.py → src/lift_parser.py
- `TestRecovery` --uses--> `LiftParser`  [INFERRED]
  tests/test_recovery.py → src/lift_parser.py

## Import Cycles
- None detected.

## Hyperedges (group relationships)
- **Jeff Nippard Training Ecosystem** — jeff_nippard_powerbuilding_3_0_5x_program, jeff_nippards_back_hypertrophy_program, jeff_nippards_chest_hypertrophy_program, jeff_nippards_shoulder_hypertrophy_program, jeff_nippards_bench_press_specialization_program [INFERRED 0.95]
- **Fitness and Physiology Knowledge Base** — anatomy_and_physiology_2e_student_solution_guide_anatomy_physiology_guide, anatomyandphysiology_lr_anatomy_physiology_textbook, arm_hypertrophy_program_workouts_for_bigger_and_stronger_arms_jeff_nippard_arm_hypertrophy_program, forearm_hypertrophy_guide_jeff_nippard_forearm_hypertrophy_guide [INFERRED 0.90]
- **ISSN Sports Nutrition Guidelines** — issn_beta_alanine_position_stand, issn_caffeine_position_stand, issn_creatine_position_stand, issn_diets_and_body_composition_position_stand, issn_nutrient_timing_position_stand, issn_protein_and_exercise_position_stand [EXTRACTED 1.00]
- **Hypertrophy Training Protocols** — full_body_high_frequency_program_jeff_nippard, fundamentals_hypertrophy_program_jeff_nippard [EXTRACTED 0.90]
- **Jeff Nippard Training Programs** — mens_shoulder_hypertrophy_program_jeff_nippard, powerbuilding_system_4xweek_program_jeff_nippard, powerbuilding_2_0_5_6xweek_jeff_nippard [EXTRACTED 1.00]

## Communities (40 total, 6 thin omitted)

### Community 0 - "Adaptive Planning & Recommendations"
Cohesion: 0.06
Nodes (36): date, AdaptivePlanner, AdaptiveRecommendations, NutritionAdjustment, Adaptive planner — generates personalized nutrition and training recommendations, Analyzes user profile + weekly trends to generate adaptive recommendations., TrainingAdjustment, Compute weekly trends + adaptive recommendations for context injection. (+28 more)

### Community 1 - "API & Request Handling"
Cohesion: 0.08
Nodes (56): BaseModel, FastAPI, chat(), chat_stream(), ChatMessage, ChatRequest, ChatResponse, _get_agent_store() (+48 more)

### Community 2 - "Exercise Retrieval"
Cohesion: 0.06
Nodes (35): ExerciseEntry, ExerciseEntry, ExerciseRetriever, get_exercise_retriever(), Exercise retriever for FitZone. Provides search, filter, and format_for_llm met, Build TF-IDF index over exercises., TF-IDF search over exercise entries.         Searches by name, category, muscle, Structured filter over exercise entries.         All filters are AND-combined. (+27 more)

### Community 3 - "Nutrition Retrieval"
Cohesion: 0.06
Nodes (35): NutritionEntry, get_nutrition_retriever(), NutritionEntry, NutritionRetriever, Nutrition retriever for FitZone. Provides search, filter, and format_for_llm me, Build TF-IDF index over nutrition entries., TF-IDF search over nutrition entries.         Returns top-k matching entries., Structured filter over nutrition entries.         All filters are AND-combined. (+27 more)

### Community 4 - "Progression & 1RM Computation"
Cohesion: 0.07
Nodes (32): acute_chronic_workload_ratio(), acwr_risk(), brzycki_1rm(), epley_1rm(), estimate_1rm(), intensity_relative_volume(), lombardi_1rm(), oconner_1rm() (+24 more)

### Community 5 - "PubMed Research Client"
Cohesion: 0.11
Nodes (14): Element, PubMedArticle, PubMedClient, PubMed API client for live biomedical literature lookups. https://pubmed.ncbi.nl, Search PubMed and format article abstracts for RAG context., Retry a callable with linear backoff on transient errors only., with_retries(), T (+6 more)

### Community 6 - "Build & Knowledge Pipeline"
Cohesion: 0.12
Nodes (14): Path, download_pdf(), main(), main(), DocumentChunk, _extract_pdf_chunks(), _file_hash(), KnowledgeRetriever (+6 more)

### Community 7 - "Intent Routing & LLM Setup"
Cohesion: 0.10
Nodes (21): ChatGroq, Domain, _sanitize_reference_context(), get_intent_router(), IntentRouter, Two-layer Intent Router for FitZone.  Layer 1 ? Topic scope check: Is this que, Quick heuristic scope classification., LLM-based scope classification fallback. (+13 more)

### Community 8 - "Formula Calculator"
Cohesion: 0.10
Nodes (13): FormulaCalculator, FormulaResult, Special handler for calorie targets by goal., Special handler for protein target., Navy body fat formula for men., Navy body fat formula for women., Search formulas by keyword., Result of a formula calculation. (+5 more)

### Community 9 - "Nutrition Data Ingestion"
Cohesion: 0.15
Nodes (18): build_static_nutrition_db(), _download_usda_api(), _download_usda_zip(), ingest_nutrition(), NutritionEntry, Nutrition data ingestion script for FitZone. Downloads and normalizes USDA Food, Safely convert a value to float., Build a comprehensive static nutrition database from curated data.     This cov (+10 more)

### Community 10 - "Lift Log Parsing"
Cohesion: 0.16
Nodes (13): _extract_exercise_name(), is_lift_log(), _looks_like_sets_reps(), _normalize_exercise(), _parse_single_chunk(), ParsedLift, ParsedSet, Natural-language parser for workout lift logs.  Handles patterns like:   - I (+5 more)

### Community 11 - "Session Store"
Cohesion: 0.16
Nodes (12): Any, _lift_to_dict(), Retrieve a session by ID., Get all logged entries for a specific exercise in a session., Get all logged entries for an exercise across ALL sessions., List all sessions (lightweight: id + date + lift count)., Delete a session. Returns True if it existed., Store and retrieve workout sessions per user/client. (+4 more)

### Community 12 - "Configuration & Logging"
Cohesion: 0.16
Nodes (14): Logger, Central configuration for FitZone Chatbot., log_event(), Structured logging for FitZone agent operations., Configure application logging once., Emit a structured JSON log line., setup_logging(), Retry helpers for external API calls. (+6 more)

### Community 13 - "Personality Modes"
Cohesion: 0.18
Nodes (10): get_personality(), get_personality_prompt(), list_personalities(), Personality, Motivational Personality Modes for FitZone Chatbot.  Provides different coachi, Get personality by mode string. Returns Coach as default., Get the prompt addition for a personality mode., List all available personalities. (+2 more)

### Community 14 - "Formula Registry"
Cohesion: 0.18
Nodes (11): format_formula_detail(), Formula, get_formula(), Formula registry and transparency mode for Show Your Work feature.  Provides s, A structured formula definition., Look up a formula by ID., Search formulas by keyword match in name, equation, or description., Format a formula for display in science mode. (+3 more)

### Community 15 - "Open Food Facts Client"
Cohesion: 0.22
Nodes (6): FoodProduct, OpenFoodFactsClient, Open Food Facts API client for live food and nutrition lookups. https://world.o, Search Open Food Facts for a user query.          Returns:             (forma, Search Open Food Facts and format nutrition data for RAG context., _to_float()

### Community 16 - "Agent Core"
Cohesion: 0.20
Nodes (13): BaseMessage, AgentResponse, _elapsed_ms(), _extract_user_profile(), get_agent(), FitZone Fitness AI Agent — scoped guardrail/router, RAG retrieval, and LLM gener, Extract key user metrics from conversation history for context injection., Convenience wrapper returning plain text (backward compatible). (+5 more)

### Community 17 - "Safety Guardrails"
Cohesion: 0.22
Nodes (12): check_safety(), Wellness safety guardrails — crisis escalation and medical boundaries., Run deterministic safety checks before any LLM call., SafetyCheck, SafetyLevel, StrEnum, Tests for safety guardrails., test_crisis_blocks_chest_pain() (+4 more)

### Community 18 - "Recovery Analysis"
Cohesion: 0.21
Nodes (10): assess_recovery(), compute_weekly_volumes(), Assess recovery status from weekly volume data.      Requires at least 5 weeks, Build recovery context string for agent injection.      Returns None if no ses, Training volume for a single week., Compute training volume per week from ALL session history.      Returns volume, recovery_context_for_agent(), WeeklyVolume (+2 more)

### Community 19 - "Exercise Ingestion Pipeline"
Cohesion: 0.23
Nodes (8): download_exercises(), ExerciseEntry, ingest_exercises(), Exercise database ingestion script for FitZone. Downloads exercises from the fr, Download exercises from the free-exercise-db GitHub repo., Download exercises, normalize, write JSON + TXT.     Returns (total_count, cate, A normalized exercise entry., Format as a text block for TF-IDF retrieval.

### Community 20 - "Context Building & Streaming"
Cohesion: 0.26
Nodes (5): FitnessAgent, Build exercise context for exercise lookup queries., Build formula context for calculation queries., Detect lift logs, store them, and build progression context.          Returns:, Stream response tokens. Yields full text on early blocks/errors.

### Community 22 - "Input Validation"
Cohesion: 0.29
Nodes (9): Input validation and basic prompt-injection filtering., Validate and lightly sanitize user input., validate_user_input(), ValidationResult, Tests for input validation., test_accepts_normal_fitness_query(), test_rejects_empty_input(), test_rejects_overlong_input() (+1 more)

### Community 23 - "Jeff Nippard Training Programs"
Cohesion: 0.24
Nodes (10): Jeff Nippard Powerbuilding 3.0 5x Program, Jeff Nippard Training Methodology, Jeff Nippard's Back Hypertrophy Program, Jeff Nippard's Bench Press Specialization Program, Jeff Nippard's Chest Hypertrophy Program, Jeff Nippard's Shoulder Hypertrophy Program, Men's Shoulder Hypertrophy Program, Powerbuilding 2.0 5-6xweek (+2 more)

### Community 24 - "WGER Exercise Import"
Cohesion: 0.33
Nodes (5): HTMLParser, fetch_json(), HTMLStripper, main(), strip_tags()

### Community 25 - "API Tests"
Cohesion: 0.22
Nodes (5): Tests for the Render-ready FitZone API., History exceeding max_length=20 should be rejected by validation., Streaming endpoint should return 200 with text/event-stream content type., test_chat_rejects_invalid_history_length(), test_chat_stream_returns_stream()

### Community 26 - "Health Checks"
Cohesion: 0.43
Nodes (6): warmup_agent(), cheap_check(), expensive_check(), main(), Fast checks: env vars + filesystem. No network calls., Slow checks: full agent warmup including Groq LLM call.

### Community 27 - "Anatomy & Physiology Knowledge"
Cohesion: 0.40
Nodes (6): Anatomy and Physiology 2e Student Solution Guide, Anatomy and Physiology Textbook (LR), Arm Hypertrophy Program (Jeff Nippard), Forearm Hypertrophy Guide (Jeff Nippard), Human Anatomy, Muscular Hypertrophy

### Community 28 - "Test Fixtures"
Cohesion: 0.33
Nodes (5): client(), _env_setup(), Shared fixtures for FitZone test suite., Provide valid env vars so the FastAPI lifespan can start under TestClient., Return a TestClient with a mocked agent response.

### Community 30 - "Training Programs & Supplements"
Cohesion: 0.67
Nodes (3): Full Body High Frequency Program (Jeff Nippard), Fundamentals Hypertrophy Program (Jeff Nippard), ISSN Position Stand: Safety and Efficacy of Creatine Supplementation

### Community 31 - "ISSN Nutrition Position Stands"
Cohesion: 0.67
Nodes (3): ISSN Position Stand: Diets and Body Composition, ISSN Position Stand: Nutrient Timing, ISSN Position Stand: Protein and Exercise

## Knowledge Gaps
- **15 isolated node(s):** `Jeff Nippard Powerbuilding 3.0 5x Program`, `Jeff Nippard's Back Hypertrophy Program`, `Jeff Nippard's Chest Hypertrophy Program`, `Jeff Nippard's Shoulder Hypertrophy Program`, `Jeff Nippard's Bench Press Specialization Program` (+10 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **6 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `SessionStore` connect `Session Store` to `Adaptive Planning & Recommendations`, `API & Request Handling`, `Progression & 1RM Computation`, `Build & Knowledge Pipeline`, `Intent Routing & LLM Setup`, `Lift Log Parsing`, `Agent Core`, `Recovery Analysis`, `Context Building & Streaming`?**
  _High betweenness centrality (0.095) - this node is a cross-community bridge._
- **Why does `PubMedClient` connect `PubMed Research Client` to `Agent Core`, `API & Request Handling`, `Context Building & Streaming`, `Intent Routing & LLM Setup`?**
  _High betweenness centrality (0.067) - this node is a cross-community bridge._
- **Why does `recommend_progression()` connect `Progression & 1RM Computation` to `Agent Core`, `API & Request Handling`, `Session Store`, `Context Building & Streaming`?**
  _High betweenness centrality (0.049) - this node is a cross-community bridge._
- **Are the 23 inferred relationships involving `SessionStore` (e.g. with `ChatMessage` and `ChatRequest`) actually correct?**
  _`SessionStore` has 23 INFERRED edges - model-reasoned connections that need verification._
- **Are the 20 inferred relationships involving `ChatTurn` (e.g. with `ChatMessage` and `ChatRequest`) actually correct?**
  _`ChatTurn` has 20 INFERRED edges - model-reasoned connections that need verification._
- **Are the 10 inferred relationships involving `UserProfile` (e.g. with `AdaptivePlanner` and `AdaptiveRecommendations`) actually correct?**
  _`UserProfile` has 10 INFERRED edges - model-reasoned connections that need verification._
- **Are the 10 inferred relationships involving `TestUserProfile` (e.g. with `AdaptivePlanner` and `NutritionAdjustment`) actually correct?**
  _`TestUserProfile` has 10 INFERRED edges - model-reasoned connections that need verification._