from __future__ import annotations

import argparse
import shutil
from dataclasses import dataclass

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
        raise SystemExit(
            "Stockfish не найден. Установи: brew install stockfish"
            "или передай путь: --engine /path/to/stockfish"
            )
    return exe

def score_to_cp(info_score: chess.engine.PovScore | None, turn: bool) -> int | None:
    if info_score is None:
        return None
    s = info_score.pov(turn)
    val = s.score(mate_score=100000)
    return int(val) if val is not None else None

def suggest_move(
        fen: str,
        engine_path: str | None = None,
        elo: int = 1000,
        think_ms: int = 200,
        k: int = 3
        ) -> SuggestionPack:
    
    board = chess.Board(fen)

    if board.is_game_over():
        raise ValueError(f"Партия уже закончина: {board.result()}")
    
    path = find_stockfish(engine_path)

    with chess.engine.SimpleEngine.popen_uci(path) as engine:
        mode = configure_strength(engine, elo)
        limit = chess.engine.Limit(time=think_ms / 1000.0)


        if k <= 1:
            info = engine.analyse(board, limit)
            infos = [info]
        else:
            infos = engine.analyse(board, limit, multipv=k)
        
        lines: list[LineSuggestion] = []

        if k == 1:
            info = engine.analyse(board, limit)
            move = info["pv"][0]
            lines.append(
                LineSuggestion(
                    move_uci=move.uci(),
                    move_san=board.san(move),
                    score_cp=score_to_cp(info.get("score"), board.turn),
                )
            )
        else:
            infos = engine.analyse(board, limit, multipv=k)
            infos = sorted(infos, key=lambda d: d.get("multipv", 999))

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



def configure_strength(engine: chess.engine.SimpleEngine, elo: int) -> str:

    #tms = suggest_move(fen)
    # включаем лимит силы, если опция есть
    if "UCI_LimitStrength" in engine.options:
        engine.configure({"UCI_LimitStrength": True})

    # пробуем Elo, но учитываем min/max конкретной сборки
    if "UCI_Elo" in engine.options:
        opt = engine.options["UCI_Elo"]
        min_elo = getattr(opt, "min", None)
        max_elo = getattr(opt, "max", None)
        applied = max(min_elo, min(max_elo, elo))

        # if min_elo is not None:
        #     applied = max(applied, int(min_elo))
        # if max_elo is not None:
        #     applied = min(applied, int(max_elo))

        engine.configure({"UCI_Elo": applied})
        return f"UCI_Elo={applied}"

    # fallback: Skill Level
    if "Skill Level" in engine.options:
        # стартовое приближение под "слабый человек"
        skill = 5
        engine.configure({"Skill Level": skill})

        return f"Skill Level={skill}"

    return "default (no strength options)"

def parse_user_move(board: chess.Board, s: str) -> chess.Move:
    s = s.strip()
    s = norm_san(s)

    try:
        move = chess.Move.from_uci(s)
        if move in board.legal_moves:
            return move
    except ValueError:
        ...

    try:
        move = board.parse_san(s)
        if move in board.legal_moves:
            return move
    except ValueError:
        ...

    raise ValueError("Невалидный ход. Введи SAN (e4, Nf3) или UCI (e2e4, g1f3).")

def play_console(engine_path: str | None, elo: int, think_ms: int) -> None:
    board = chess.Board()
    path = find_stockfish(engine_path)

    with chess.engine.SimpleEngine.popen_uci(path) as engine:
        mode = configure_strength(engine, elo)
        print(f"[engine] strength: {mode}, think_ms={think_ms}")
        print("Вводи ходы в SAN (e4, Nf3) или UCI (e2e4, g1f3). Выход: 'quit'.")

        while not board.is_game_over():
            print("\n" + str(board))
            print(f"Ход: {'Белые' if board.turn else 'Черные'}")
            # ход человека
            user = input("Ваш ход:-> ".strip())
            if user.lower() in {"q","quit","exit"}:
                print("Выход...")
                return
            try:
                u_move = parse_user_move(board, user)
            except ValueError as e:
                print(f"❌ {e}")
                continue # не падаем, а проосим ввод снова
            
            u_san = board.san(u_move)
            board.push(u_move)
            print(f"Вы: {u_san} ({u_move.uci()})")

            if board.is_game_over():
                break
            # ход движка
            limit = chess.engine.Limit(time=think_ms / 1000.0)
            result = engine.play(board, limit)
            engine_move = result.move
            engine_san = board.san(engine_move)
            board.push(engine_move)
            print(f"🤖 Движок: {engine_san} ({engine_move.uci()})")
        
        print("\nИгра окончена:", board.result())

def norm_san(s: str) -> str:
    s = s.strip()

    s = s.replace("0-0-0", "O-O-O").replace("0-0", "O-O")

    # нормализация: "NF3" -> "Nf3"
    # фигуры KQBNR, остальное лучше не трогаем
    if s and s[0] in "KQBNR":
        s = s[0] + s[1:].lower()

    return s


def main() -> None:
    ap = argparse.ArgumentParser(description="Подсказка хода Stockfish (~Elo) по FEN")
    ap.add_argument("--fen", help="FEN позиции в кавычках")
    ap.add_argument("--elo", type=int, default=1000, help="Сила движка (пример: 1000)")
    ap.add_argument("--think-ms", type=int, default=200, help="Время на ход в мс")
    ap.add_argument("--engine", default=None, help="Путь к stockfish (если не в PATH)")
    ap.add_argument("--topk", type=int, default=3, help="Сколько вариантов показать (MultiPV)")
    ap.add_argument("--play", action="store_true", help="Играть против движка в консоли")
    ap.add_argument("--start-fen", default=chess.STARTING_FEN, help="Начальная позиция (FEN)")

    args = ap.parse_args()
    # === РЕЖИМ ИГРЫ ===
    if args.play:
        play_console(
            engine_path=args.engine,
            elo=args.elo,
            think_ms=args.think_ms,
        )
        return
    #=== РЕЖИМ ПОДСКАЗОК ===
    if not args.fen:
        ap.error("--fen обязателен, если не используется --play")


    pack = suggest_move(
        fen=args.fen,
        engine_path=args.engine,
        elo=args.elo,
        think_ms=args.think_ms,
        k=args.topk,
    )

    print(f"[engine] strength: {pack.mode}, think_ms={pack.think_ms}")
    for i, line in enumerate(pack.lines, start=1):
        print(f"{i}) SAN: {line.move_san:6} | UCI: {line.move_uci}", end="")
        if line.score_cp is None:
            print(" | Eval: mate/unknown")
        else:
            print(f" | Eval(cp): {line.score_cp:+d}")
    
    if args.play:
        play_console(args.engine, args.elo, args.think_ms)
        return



if __name__== "__main__":
    main()