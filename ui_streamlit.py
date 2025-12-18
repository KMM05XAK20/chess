import streamlit as st
import chess
import chess.engine
import chess.svg
import streamlit.components.v1 as components
import shutil
from chess_core import start_engine, stop_engine, parse_user_move, suggest_topk, engine_reply_move
from fen_hint import find_stockfish, configure_strength

st.set_page_config(page_title="Chess Helper", layout="centered")
st.title("♟️ Chess Helper (подсказчик + игра)")

# =========================
# Session state INIT
# =========================

if "engine" not in st.session_state:
    st.session_state.engine = None

if "engine_mode" not in st.session_state:
    st.session_state.engine_mode = ""
    
if "board" not in st.session_state:
    st.session_state.board = chess.Board()

if "last_move" not in st.session_state:
    st.session_state.last_move = None

if "log" not in st.session_state:
    st.session_state.log = []

if "suggestions" not in st.session_state or not isinstance(st.session_state.suggestions, list):
    st.session_state.suggestions = []
# =========================

def require_engine(engine_path: str | None, elo: int):

    if st.session_state.engine is None:
        eng, mode = start_engine(engine_path, elo)
        st.session_state.engine = eng
        st.session_state.engine_mode = mode
    return st.session_state.engine, st.session_state.engine_mode

def compute_suggestions(board: chess.Board, engine_path: str | None, elo: int, think_ms: int, topik:int) -> None:
    engine, mode = require_engine(engine_path, elo)
    limit = chess.engine.Limit(time=think_ms / 1000.0)

    infos = engine.analyse(board, limit, multipv=topk) if topk > 1 else [engine.analyse(board, limit)]
    infos = sorted(infos, key=lambda d: d.get("multipv", 1))

    sugg: list[tuple[str, str, int | None]] = []

    for info in infos:
        pv = info.get("pv")
        if not pv:
            continue
        m = pv[0]
        uci = m.uci()
        san = board.san(m)

        score = info.get("score")
        cp = None
        if score is not None:
            val = score.pov(board.turn).score(mate_score=10000)
            cp = int(val) if val is not None else None
        
        sugg.append((uci, san, cp))

    st.session_state.suggestions = []
    st.session_state.suggestions = sugg
    st.session_state.suggestions = mode
# --------- Состояние доски

board: chess.Board = st.session_state.board


# --------- Отображение
st.subheader("Позиция")
st.code(board.fen())
st.text(str(board))

last = st.session_state.get("last_move")
svg_bytes = chess.svg.board(board=board, size=420, lastmove=last,)
components.html(svg_bytes, height=460, width=460)
with st.expander("Показать текстовую доску"):
    st.text(str(board))



def get_engine(engine_path: str | None, elo: int):
    if "engine" not in st.session_state:
        eng, mode = start_engine(engine_path, elo)
        st.session_state.engine = eng
        st.session_state.engine_mode = mode
    return st.session_state.engine, st.session_state.engine_mode

@st.cache_resource
def get_engine_cache(engine_path: str | None, elo: int) -> tuple[chess.engine.SimpleEngine, str]:
    path = engine_path or shutil.which("stockfish")
    if not path:
        raise RuntimeError("Stockfish не найден. Установи: brew install stockfish")
    
    eng = chess.engine.SimpleEngine.popen_uci(path)

    mode = configure_strength(eng, elo)
    return eng, mode


# --------- Настройки справа
with st.sidebar:
    st.header("Настройки")
    engine_path = st.text_input("Путь к Stockfish (если не в PATH)", value="", key="engine_path")
    elo = st.slider("Целевой Elo (клампится)", 800, 2000, 1000, 50, key="elo")
    think_ms = st.slider("Время на ход (мс)", 20, 1000, 200, 10, key="think_ms")
    topk = st.slider("Подсказок", 1, 5, 3, key="topk")
    trainer_mode = st.checkbox("Режим тренера (показывать подсказки перед ходом)", value=True)
    auto_reply = st.checkbox("Авто-ответ движка после моего хода",value=False)

    st.sidebar.write("suggestions type:", type(st.session_state.suggestions))
engine_path = engine_path.strip() or None



sig = (engine_path, elo)

if "engine_sig" not in st.session_state:
    st.session_state.engine_sig = sig
elif st.session_state.engine_sig != sig:
    get_engine_cache.clear()
    st.session_state.engine_sig = sig


col1, col2, col3 = st.columns(3)
with col1:
    if st.button("Сброс"):
        stop_engine(st.session_state.engine)
        st.session_state.engine = None
        st.session_state.engine_mode = ""
        st.session_state.board = chess.Board()
        st.session_state.log = []
        st.session_state.last_move = None
        st.rerun()
    if st.button("Undo"):
        board.pop()
        st.session_state.last_move = board.peek() if board.move_stack else None
        st.session_state.log.append("↩️ Undo")
        st.rerun()

with col2:
    if st.button("Подсказки"):
        try:
            engine, mode = get_engine(engine_path, elo)
            limit = chess.engine.Limit(time=think_ms / 1000.0)

            infos = engine.analyse(board, limit, multipv=topk) if topk > 1 else [engine.analyse(board, limit)]
            infos = sorted(infos, key=lambda d: d.get("multipv", 1))

            st.session_state.suggestions = []
            for info in infos:
                pv = info.get("pv")
                if not pv:
                    continue
                m = pv[0]
                san = board.san(m)
                st.session_state.suggestions.append((m.uci(), board.san(m), cp))

            if st.session_state.suggestions:
                st.subheader("Подсказки (кликни чтобы сделать ход)")
                for uci in st.session_state.suggestions:
                    m = chess.Move.from_uci(uci)
                    label = board.san(m) if m in board.legal_moves else uci
                    if st.button(f"➡️ {label} ({uci})", key=f"sug_{uci}"):
                        # применяем ход
                        san = board.san(m)
                        board.push(m)
                        st.session_state.last_move = m
                        st.session_state.log.append(f"💡 Подсказка: {san} ({uci})")
                        st.rerun()


            st.info(f"[engine] {mode}, think_ms={think_ms}")
            for i, info in enumerate(infos, start=1):
                pv = info.get("pv")
                if not pv:
                    continue
                m = pv[0]
                san = board.san(m)
                score = info.get("score")
                cp = None
                if score is not None:
                    val = score.pov(board.turn).score(mate_score=100000)
                    cp = int(val) if val is not None else None
                eval_txt = "mate/unknown" if cp is None else f"{cp:+d} cp"
                st.write(f"{i}) **{san}** ({m.uci()}) — {eval_txt}")
        except Exception as e:
            st.error(str(e))

with col3:
    if st.button("Ход движка"):
        try:
            engine, mode = get_engine(engine_path, elo)
            engine, mode = get_engine_cache(engine_path, elo)
            engine, mode = require_engine(engine_path, elo)
            limit = chess.engine.Limit(time=think_ms / 1000.0)
            result = engine.play(board, limit)
            m = result.move
            san = board.san(m)
            board.push(m)
            st.session_state.last_move = m
            st.session_state.log.append(f"🤖 {san} ({m.uci()}) [{mode}]")
            st.rerun()
        except Exception as e:
            st.error(str(e))

if trainer_mode and not board.is_game_over():
    try:
        compute_suggestions(board, engine_path, elo, think_ms, topk)
    except Exception as e:
        st.warning(f"Не смог получить подсказки: {e}")

st.subheader("Сделать ход")
move_text = st.text_input("Ваш ход (SAN или UCI)", value="", placeholder="например: e4 или g1f3")

if st.button("Применить ход"):
    try:
        m = parse_user_move(board, move_text)
        san = board.san(m)
        board.push(m)
        engine, mode = require_engine(engine_path, elo)
        limit = chess.engine.Limit(time=think_ms / 1000.0)
        em = res.move
        es = board.san(em)
        board.push(em)
        if auto_reply and not board.is_game_over():
            engine, mode = require_engine(engine_path, elo)
            limit = chess.engine.Limit(time=think_ms / 1000.0)
            res = engine.play(board, limit)
            em = res.move
            es = board.san(em)
            board.push(es)
            st.session_state.last_move = em
            st.session_state.log.append(f"🙂 {es} ({em.uci()}) [{mode}]")
        st.session_state.last_move = em
        st.session_state.last_move = m
        st.session_state.log.append(f"🙂 {es} ({em.uci()}) [{mode}]")
        st.session_state.log.append(f"🙂 {san} ({m.uci()})")
        st.rerun()
    except Exception as e:
        st.error(str(e))

if st.button("Отменить ход"):
    if board.move_stack:
        board.pop()
        st.rerun()

try:
    st.session_state.board = chess.Board(move_text) #???? fen_text - not found, fen_text or move_text???
except ValueError:
    st.error("Неверный FEN")

st.subheader("Лог ходов")
for line in st.session_state.log[-20:]:
    st.write(line)

if board.is_game_over():
    st.success(f"Игра окончена: {board.result()}")

st.sidebar.write("engine is None?", st.session_state.engine is None)


if trainer_mode and len(st.session_state.suggestions) > 0:
    st.subheader("Подсказки")
    st.caption(f"[engine] {st.session_state.engine_mode}, think_ms={think_ms}")

    sug = st.session_state.get("suggestions", [])
    if isinstance(sug, str):
        st.session_state.suggestions = []
        sug = []
    if not isinstance(sug, list):
        st.session_state = []
        sug = []

    for item in sug:
        if isinstance(item, tuple) and len(item) == 3:
            uci, san, cp = item
        else:
            uci = str(item)
            m = chess.Move.from_uci(uci)
            san = board.san(m) if m in board.legal_moves else uci
            cp = None
        eval_txt = "mate/unknown" if cp is None else f"{cp:+d} cp"
        if st.button("f{san} ({eval_txt})", key=f"sug_{uci}"):
            m = chess.Move.from_uci(uci)
            san = board.san(m) if m in board.legal_moves else uci
            cp = None
            if m not in board.legal_moves:
                st.error("Подсказка уже не актуальна (позиция изменилась).")
                st.stop()

            board.push(m)
            st.session_state.last_move = m
            st.session_state.log.append(f"Подсказка:: {san} ({uci})")

            # авто-ответ движке
            if auto_reply and not board.is_game_over():
                engine, mode = require_engine(engine_path, elo)
                limit = chess.engine.Limit(time=think_ms / 1000.0)
                res = engine.play(board, limit)
                em = res.move
                es = board.san(m)
                board.push(m)
                st.session_state.last_move = em
                st.session_state.log.append(f"{es} ({em.uci()}) [{mode}]")
            st.rerun()
