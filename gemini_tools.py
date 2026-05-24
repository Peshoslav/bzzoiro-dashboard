"""
Gemini Function Calling — Bzzoiro sports data tools.
Implements the same capabilities as the MCP server but via REST API,
so no OAuth is required — we reuse the existing BZZOIRO_API_KEY.

Usage:
    from gemini_tools import run_gemini_with_tools
    answer = run_gemini_with_tools(client, system_prompt, user_question)
"""
from __future__ import annotations
import json
from typing import Any, Dict, List, Optional
import streamlit as st

# ── Tool implementations (REST → structured data) ─────────────────

def _tool_get_predictions(event_id: int) -> Dict:
    from api import get_prediction
    return get_prediction(event_id)

def _tool_compare_odds(event_id: int) -> Dict:
    from api import get_odds_comparison
    return get_odds_comparison(event_id)

def _tool_get_lineups(event_id: int) -> Dict:
    from api import get_event_lineups
    return get_event_lineups(event_id)

def _tool_get_incidents(event_id: int) -> List[Dict]:
    from api import get_event_incidents
    return get_event_incidents(event_id)

def _tool_get_shotmap(event_id: int) -> List[Dict]:
    from api import get_event_shotmap
    return get_event_shotmap(event_id)

def _tool_get_team_fixtures(team_name: str, last_n: int = 5) -> List[Dict]:
    from api import get_team_fixtures
    return get_team_fixtures(team_name=team_name, last_n=last_n)

def _tool_get_standings(league_name: str) -> List[Dict]:
    """Get league standings by league name (searches by name)."""
    from api import get_leagues, get_standings
    leagues = get_leagues()
    match = next((l for l in leagues
                  if league_name.lower() in (l.get("name") or "").lower()), None)
    if match:
        return get_standings(match["id"])
    return []

def _tool_get_player_stats(event_id: int) -> List[Dict]:
    from api import get_event_player_stats
    return get_event_player_stats(event_id)

def _tool_get_h2h(home_team: str, away_team: str, last_n: int = 5) -> List[Dict]:
    from api import get_h2h
    return get_h2h(None, None, home_name=home_team, away_name=away_team, last_n=last_n)

def _tool_get_live_scores() -> List[Dict]:
    from api import get_live_events
    return get_live_events()


# ── Tool registry ─────────────────────────────────────────────────

TOOL_FUNCTIONS = {
    "get_predictions":    lambda a: _tool_get_predictions(**a),
    "compare_odds":       lambda a: _tool_compare_odds(**a),
    "get_lineups":        lambda a: _tool_get_lineups(**a),
    "get_incidents":      lambda a: _tool_get_incidents(**a),
    "get_shotmap":        lambda a: _tool_get_shotmap(**a),
    "get_team_fixtures":  lambda a: _tool_get_team_fixtures(**a),
    "get_standings":      lambda a: _tool_get_standings(**a),
    "get_player_stats":   lambda a: _tool_get_player_stats(**a),
    "get_h2h":            lambda a: _tool_get_h2h(**a),
    "get_live_scores":    lambda a: _tool_get_live_scores(),
}


# ── Gemini function declarations ──────────────────────────────────

def _build_tools():
    """Build google.genai Tool object with all function declarations."""
    from google.genai import types

    def _obj(*required, **props):
        return types.Schema(
            type=types.Type.OBJECT,
            properties={k: types.Schema(**v) for k, v in props.items()},
            required=list(required),
        )

    declarations = [
        types.FunctionDeclaration(
            name="get_predictions",
            description="Вземи ML прогноза (CatBoost) за мач по неговото ID. "
                        "Връща вероятности за резултат, BTTS, Over/Under и др.",
            parameters=_obj("event_id",
                event_id=dict(type=types.Type.INTEGER,
                              description="ID на мача (event_id)"),
            ),
        ),
        types.FunctionDeclaration(
            name="compare_odds",
            description="Сравни коефициентите от всички букмейкъри за даден мач.",
            parameters=_obj("event_id",
                event_id=dict(type=types.Type.INTEGER, description="ID на мача"),
            ),
        ),
        types.FunctionDeclaration(
            name="get_lineups",
            description="Вземи потвърдените или прогнозираните стартови "
                        "единадесетки и за двата отбора.",
            parameters=_obj("event_id",
                event_id=dict(type=types.Type.INTEGER, description="ID на мача"),
            ),
        ),
        types.FunctionDeclaration(
            name="get_incidents",
            description="Всички инциденти от мача: голове, картони, "
                        "смени, ВАР — минута по минута.",
            parameters=_obj("event_id",
                event_id=dict(type=types.Type.INTEGER, description="ID на мача"),
            ),
        ),
        types.FunctionDeclaration(
            name="get_shotmap",
            description="Карта на ударите с xG стойности и координати на терена.",
            parameters=_obj("event_id",
                event_id=dict(type=types.Type.INTEGER, description="ID на мача"),
            ),
        ),
        types.FunctionDeclaration(
            name="get_team_fixtures",
            description="Последните N завършили мача на отбор по неговото "
                        "ТОЧНО английско или оригинално ПЪЛНО ИМЕ.",
            parameters=_obj("team_name",
                team_name=dict(type=types.Type.STRING,
                               description="Пълното официално им на отбора"),
                last_n=dict(type=types.Type.INTEGER,
                            description="Брой мачове (default 5)"),
            ),
        ),
        types.FunctionDeclaration(
            name="get_standings",
            description="Класирането в лигата (таблица) по нейното официално "
                        "английско или оригинално ИМЕ.",
            parameters=_obj("league_name",
                league_name=dict(type=types.Type.STRING,
                                 description="Пълното или частично им на лигата"),
            ),
        ),
        types.FunctionDeclaration(
            name="get_player_stats",
            description="Статистики на всички играчи от конкретен мач "
                        "(голове, асистенции, оценка, xG, предавания и др.).",
            parameters=_obj("event_id",
                event_id=dict(type=types.Type.INTEGER, description="ID на мача"),
            ),
        ),
        types.FunctionDeclaration(
            name="get_h2h",
            description="Последните N директни срещи (H2H) между два отбора.",
            parameters=_obj("home_team", "away_team",
                home_team=dict(type=types.Type.STRING,
                               description="Пълното им на домакина"),
                away_team=dict(type=types.Type.STRING,
                               description="Пълното им на госта"),
                last_n=dict(type=types.Type.INTEGER,
                            description="Брой мачове (default 5)"),
            ),
        ),
        types.FunctionDeclaration(
            name="get_live_scores",
            description="Всички мачове, играни в момента, с текущ резултат.",
            parameters=types.Schema(type=types.Type.OBJECT, properties={}),
        ),
    ]

    return types.Tool(function_declarations=declarations)


# ── Agentic loop ──────────────────────────────────────────────────

def run_gemini_with_tools(client, system_prompt: str,
                          user_question: str,
                          history: Optional[List[Dict]] = None,
                          max_rounds: int = 4) -> str:
    """
    Run a Gemini conversation with tool calling enabled.
    Gemini can call up to max_rounds tools before giving a final answer.
    Returns the final text response.
    """
    try:
        from google.genai import types

        tool   = _build_tools()
        config = types.GenerateContentConfig(
            tools=[tool],
            system_instruction=system_prompt,
        )

        # Build conversation contents
        contents = []
        if history:
            for msg in history[-8:]:   # last 4 turns
                role = "user" if msg["role"] == "user" else "model"
                contents.append(types.Content(
                    role=role,
                    parts=[types.Part.from_text(msg["content"])],
                ))
        contents.append(types.Content(
            role="user",
            parts=[types.Part.from_text(user_question)],
        ))

        for _round in range(max_rounds):
            response = client.models.generate_content(
                model="gemini-3.1-flash-lite",
                contents=contents,
                config=config,
            )

            candidate = response.candidates[0]
            parts      = candidate.content.parts if candidate.content else []

            # Check for function calls
            fn_calls = [p for p in parts if hasattr(p, "function_call") and p.function_call]
            if not fn_calls:
                # No tool calls → final answer
                text_parts = [p.text for p in parts if hasattr(p, "text") and p.text]
                return "\n".join(text_parts) or "Нямаш отговор."

            # Execute all function calls in this round
            fn_results = []
            for part in fn_calls:
                fn      = part.function_call
                fn_name = fn.name
                fn_args = dict(fn.args) if fn.args else {}

                try:
                    result = TOOL_FUNCTIONS[fn_name](fn_args)
                    result_str = json.dumps(result, ensure_ascii=False, default=str)
                    # Truncate large results
                    if len(result_str) > 4000:
                        result_str = result_str[:4000] + "…(съкратено)"
                except KeyError:
                    result_str = f"Неизвестна функция: {fn_name}"
                except Exception as e:
                    result_str = f"Грешка при {fn_name}: {e}"

                fn_results.append(
                    types.Part.from_function_response(
                        name=fn_name, response={"result": result_str}
                    )
                )

            # Add model turn (with fn calls) + tool results to conversation
            contents.append(types.Content(
                role="model", parts=parts
            ))
            contents.append(types.Content(
                role="user",
                parts=fn_results,
            ))

        # Max rounds reached — ask for final answer without tools
        final = client.models.generate_content(
            model="gemini-3.1-flash-lite",
            contents=contents,
        )
        return final.text or "Достигнат лимит на итерации."

    except Exception as e:
        return f"❌ Грешка: {e}"
