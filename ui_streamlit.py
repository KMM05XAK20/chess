import streamlit as st
import chess
import chess.engine
import chess.svg
import streamlit.components.v1 as components
from chess_core import parse_user_move, suggest_topk, engine_reply_move
from fen_hint import find_stockfish, configure_strength

st.set_page_config(page_title="Chess Helper", layout="centered")
st.title("♟️ Chess Helper (подсказчик + игра)")


# --------- Состояние доски
if "board" not in st.session_state:
    st.session_state.board = chess.Board()
if "log" not in st.session_state:
    st.session_state.log = []

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


# --------- Настройки справа
with st.sidebar:
    st.header("Настройки")
    engine_path = st.text_input("Путь к Stockfish (если не в PATH)", value="")
    elo = st.slider("Целевой Elo (будет клампиться)", min_value=800, max_value=2000, value=1000, step=50)
    think_ms = st.slider("Время на ход (мс)", min_value=20, max_value=1000, value=200, step=10)
    topk = st.slider("Сколько подсказок", min_value=1, max_value=5, value=3)

engine_path = engine_path.strip() or None




col1, col2, col3 = st.columns(3)
with col1:
    if st.button("Сброс"):
        st.session_state.board = chess.Board()
        st.session_state.log = []
        st.rerun()

with col2:
    if st.button("Подсказки"):
        try:
            pack = suggest_topk(board, engine_path, elo, think_ms, k=topk)
            st.info(f"[engine] {pack.mode}, think_ms={pack.think_ms}")
            for i, line in enumerate(pack.lines, start=1):
                eval_txt = "mate/unknown" if line.score_cp is None else f"{line.score_cp:+d} cp"
                st.write(f"{i}) **{line.move_san}**  ({line.move_uci}) — {eval_txt}")
        except Exception as e:
            st.error(str(e))

with col3:
    if st.button("Ход движка"):
        try:
            mode, m, san = engine_reply_move(board, engine_path, elo, think_ms)
            board.push(m)
            st.session_state.log.append(f"🤖 {san} ({m.uci()}) [{mode}]")
            st.rerun()
        except Exception as e:
            st.error(str(e))

st.subheader("Сделать ход")
move_text = st.text_input("Ваш ход (SAN или UCI)", value="", placeholder="например: e4 или g1f3")

if st.button("Применить ход"):
    try:
        m = parse_user_move(board, move_text)
        san = board.san(m)
        board.push(m)
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


def get_engine(engine_path, elo):
    if "engine" not in st.session_state:
        path = find_stockfish(engine_path)
        eng = chess.engine.SimpleEngine.popen_uci(path)
        st.session_state.engine = eng
        st.session_state.engine_mode = configure_strength(eng, elo)
    return st.session_state.engine, st.session_state.engine_mode
