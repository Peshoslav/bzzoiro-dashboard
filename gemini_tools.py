"""
Gemini Function Calling — Bzzoiro sports data tools.
Compatible with google-genai==2.6.0
"""
from __future__ import annotations
import json
from typing import Any, Dict, List, Optional


# ── Tool implementations ──────────────────────────────────────────

def _tool_get_predictions(event_id: int) -> Dict:
    from api import get_prediction
    return get_prediction(int(event_id))

def _tool_compare_odds(event_id: int) -> Dict:
    from api import get_odds_comparison
    return get_odds_comparison(int(event_id))

def _tool_get_lineups(event_id: int) -> Dict:
    from api import get_event_lineups
    return get_event_lineups(int(event_id))

def _tool_get_incidents(event_id: int) -> List[Dict]:
    from api import get_event_incidents
    return get_event_incidents(int(event_id))

def _tool_get_shotmap(event_id: int) -> List[Dict]:
    from api import get_event_shotmap
    return get_event_shotmap(int(event_id))

def _tool_get_team_fixtures(team_name: str, last_n: int = 5) -> List[Dict]:
    from api import get_team_fixtures
    return get_team_fixtures(team_name=str(team_name), last_n=int(last_n))

def _tool_get_standings(league_name: str) -> List[Dict]:
    from api import get_leagues, get_standings
    leagues = get_leagues()
    match = next((l for l in leagues
                  if league_name.lower() in (l.get("name") or "").lower()), None)
    if match:
        return get_standings(match["id"])
    return []

def _tool_get_player_stats(event_id: int) -> List[Dict]:
    from api import get_event_player_stats
    return get_event_player_stats(int(event_id))

def _tool_get_h2h(home_team: str, away_team: str, last_n: int = 5) -> List[Dict]:
    from api import get_h2h
    return get_h2h(None, None,
                   home_name=str(home_team), away_name=str(away_team),
                   last_n=int(last_n))

def _tool_get_live_scores() -> List[Dict]:
    from api import get_live_events
    return get_live_events()


TOOL_FUNCTIONS = {
    "get_predictions":   lambda a: _tool_get_predictions(**a),
    "compare_odds":      lambda a: _tool_compare_odds(**a),
    "get_lineups":       lambda a: _tool_get_lineups(**a),
    "get_incidents":     lambda a: _tool_get_incidents(**a),
    "get_shotmap":       lambda a: _tool_get_shotmap(**a),
    "get_team_fixtures": lambda a: _tool_get_team_fixtures(**a),
    "get_standings":     lambda a: _tool_get_standings(**a),
    "get_player_stats":  lambda a: _tool_get_player_stats(**a),
    "get_h2h":           lambda a: _tool_get_h2h(**a),
    "get_live_scores":   lambda a: _tool_get_live_scores(),
}


# ── Build Gemini Tool ──────────────────────────────────────────────
def _build_tools():
    from google.genai import types

    def _schema(**props):
        return types.Schema(
            type=types.Type.OBJECT,
            properties={k: types.Schema(**v) for k, v in props.items()},
        )

    INT = {"type": "integer"}
    STR = {"type": "string"}

    declarations = [
        types.FunctionDeclaration(
            name="get_predictions",
            description="ML прогноза (CatBoost) за вероятности: победа, равен, "
                        "загуба, BTTS, Over/Under.",
            parameters=_schema(event_id=INT),
        ),
        types.FunctionDeclaration(
            name="compare_odds",
            description="Коефициенти от всички букмейкъри за конкретен мач.",
            parameters=_schema(event_id=INT),
        ),
        types.FunctionDeclaration(
            name="get_lineups",
            description="Стартовите единадесетки и резервите и за двата отбора.",
            parameters=_schema(event_id=INT),
        ),
        types.FunctionDeclaration(
            name="get_incidents",
            description="Хронология на мача: голове, картони, смени, ВАР — "
                        "минута по минута.",
            parameters=_schema(event_id=INT),
        ),
        types.FunctionDeclaration(
            name="get_shotmap",
            description="Карта на ударите с xG стойности и координати.",
            parameters=_schema(event_id=INT),
        ),
        types.FunctionDeclaration(
            name="get_team_fixtures",
            description="Последните N завършили мача на отбор. "
                        "Подай точното официално АНГЛИЙСКО или ОРИГИНАЛНО им на отбора.",
            parameters=_schema(team_name=STR,
                               last_n={"type": "integer",
                                       "description": "Брой мачове (default 5)"}),
        ),
        types.FunctionDeclaration(
            name="get_standings",
            description="Класиране/таблица в лигата. "
                        "Подай частично или пълно им на лигата на английски.",
            parameters=_schema(league_name=STR),
        ),
        types.FunctionDeclaration(
            name="get_player_stats",
            description="Статистики на всички играчи от мача: оценка, xG, "
                        "предавания, дуели и др.",
            parameters=_schema(event_id=INT),
        ),
        types.FunctionDeclaration(
            name="get_h2h",
            description="Директни срещи между два отбора (H2H). "
                        "Подай точните имена на двата отбора.",
            parameters=_schema(
                home_team=STR, away_team=STR,
                last_n={"type": "integer", "description": "Брой мачове (default 5)"},
            ),
        ),
        types.FunctionDeclaration(
            name="get_live_scores",
            description="Всички мачове в момента с текущ резултат и минута.",
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
    Agentic loop: Gemini can call tools until it has a complete answer.
    Uses google-genai 2.6.0 compatible API (types.Part(text=...) syntax).
    """
    try:
        from google.genai import types

        tool   = _build_tools()
        config = types.GenerateContentConfig(
            tools=[tool],
            system_instruction=system_prompt,
        )

        # ── Build conversation history ────────────────────────────
        contents: List[types.Content] = []
        if history:
            for msg in history[-8:]:
                role = "user" if msg["role"] == "user" else "model"
                contents.append(types.Content(
                    role=role,
                    parts=[types.Part(text=msg["content"])]  # ← Part(text=) not from_text()
                ))

        contents.append(types.Content(
            role="user",
            parts=[types.Part(text=user_question)]
        ))

        # ── Tool calling loop ─────────────────────────────────────
        for _round in range(max_rounds):
            response = client.models.generate_content(
                model="gemini-3.1-flash-lite",
                contents=contents,
                config=config,
            )

            if not response.candidates:
                return "Няма отговор от модела."

            resp_content = response.candidates[0].content
            if not resp_content or not resp_content.parts:
                return "Празен отговор."

            parts = resp_content.parts

            # Collect function calls
            fn_calls = [
                p.function_call for p in parts
                if hasattr(p, "function_call") and p.function_call
            ]

            if not fn_calls:
                # Final text answer
                return "\n".join(
                    p.text for p in parts
                    if hasattr(p, "text") and p.text
                ) or "Нямаш отговор."

            # Add model turn (with fn calls) to history
            contents.append(types.Content(role="model", parts=parts))

            # Execute each tool call
            result_parts: List[types.Part] = []
            for fn in fn_calls:
                fn_name = fn.name
                fn_args = dict(fn.args) if fn.args else {}

                try:
                    result = TOOL_FUNCTIONS[fn_name](fn_args)
                    result_str = json.dumps(result, ensure_ascii=False, default=str)
                    if len(result_str) > 4000:
                        result_str = result_str[:4000] + "…(съкратено)"
                except KeyError:
                    result_str = f"Непознат инструмент: {fn_name}"
                except Exception as e:
                    result_str = f"Грешка при {fn_name}: {e}"

                result_parts.append(types.Part(
                    function_response=types.FunctionResponse(
                        name=fn_name,
                        response={"result": result_str},
                    )
                ))

            contents.append(types.Content(role="user", parts=result_parts))

        # Max rounds hit — get final answer without tools
        final = client.models.generate_content(
            model="gemini-3.1-flash-lite",
            contents=contents,
        )
        return final.text or "Достигнат лимит на инструменти."

    except Exception as e:
        return f"❌ Грешка: {e}"
