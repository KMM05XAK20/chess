from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping, Optional, cast
import shutil

import chess
import chess.engine


@dataclass(frozen=True)
class LineSuggestion:
    move_uci: str
    move_san: str
    score_cp: int | None


@dataclass(frozen=True)
class SuggestionPack:
    mode: str
    think_ms: int
    lines: list[LineSuggestion]


def find_stockfish(path: str | None) -> str:
    if path:
        return path
    exe = shutil.which("stockfish")
    if not exe:
        raise RuntimeError(
            "Stockfish не найден. Установи: brew install stockfish "
            "или передай путь в UI."
        )
    return exe


def configure_strength(engine: chess.engine.SimpleEngine, elo: int) -> str:
    if "UCI_LimitStrength" in engine.options:
        engine.configure({"UCI_LimitStrength": True})

    if "UCI_Elo" in engine.options:
        opt = engine.options["UCI_Elo"]
        min_elo = getattr(opt, "min", None)
        max_elo = getattr(opt, "max", None)

        applied = elo
        if min_elo is not None:
            applied = max(applied, int(min_elo))
        if max_elo is not None:
            applied = min(applied, int(max_elo))

        engine.configure({"UCI_Elo": applied})
        return f"UCI_Elo={applied}"

    if "Skill Level" in engine.options:
        skill = 5
        engine.configure({"Skill Level": skill})
        return f"Skill Level={skill}"

    return "default (no strength options)"


def score_to_cp(info_score: chess.engine.PovScore | None, turn: bool) -> int | None:
    if info_score is None:
        return None
    s = info_score.pov(turn)
    val = s.score(mate_score=100000)
    return int(val) if val is not None else None


def normalize_san(s: str) -> str:
    s = s.strip()
    s = s.replace("0-0-0", "O-O-O").replace("0-0", "O-O")
    if s and s[0] in "KQBNR":
        s = s[0] + s[1:].lower()
    return s


def parse_user_move(board: chess.Board, s: str) -> chess.Move:
    s = normalize_san(s)

    # 1) UCI
    try:
        m = chess.Move.from_uci(s)
        if m in board.legal_moves:
            return m
    except ValueError:
        pass

    # 2) SAN
    try:
        m = board.parse_san(s)
        if m in board.legal_moves:
            return m
    except ValueError:
        pass

    raise ValueError("Невалидный ход. Введи SAN (e4, Nf3) или UCI (e2e4, g1f3).")


def suggest_topk(
    board: chess.Board,
    engine_path: str | None,
    elo: int,
    think_ms: int,
    k: int = 3,
) -> SuggestionPack:
    path = find_stockfish(engine_path)

    with chess.engine.SimpleEngine.popen_uci(path) as engine:
        mode = configure_strength(engine, elo)
        limit = chess.engine.Limit(time=think_ms / 1000.0)

        infos = engine.analyse(board, limit, multipv=k) if k > 1 else [engine.analyse(board, limit)]
        infos = sorted(infos, key=lambda d: d.get("multipv", 1))

        lines: list[LineSuggestion] = []
        for info in infos:
            pv = info.get("pv")
            if not pv:
                continue
            move = pv[0]
            lines.append(
                LineSuggestion(
                    move_uci=move.uci(),
                    move_san=board.san(move),
                    score_cp=score_to_cp(info.get("score"), board.turn),
                )
            )

        return SuggestionPack(mode=mode, think_ms=think_ms, lines=lines)


def engine_reply_move(
    board: chess.Board,
    engine_path: str | None,
    elo: int,
    think_ms: int,
) -> tuple[str, chess.Move, str]:
    """
    Возвращает (mode, move, san). SAN считается ДО push.
    """
    path = find_stockfish(engine_path)

    with chess.engine.SimpleEngine.popen_uci(path) as engine:
        mode = configure_strength(engine, elo)
        limit = chess.engine.Limit(time=think_ms / 1000.0)
        result = engine.play(board, limit)
        m = result.move
        san = board.san(m)
        return mode, m, san
