# ♟️ Chess Helper — подсказчик и игра против движка

## 🇷🇺 Описание (Russian)

**Chess Helper** — учебный Python-проект, который помогает анализировать шахматные позиции и играть против движка уровня ~1000–1300 Elo.

Проект позволяет:

* 🔍 получать **топ-N подсказок ходов** (MultiPV) для любой позиции (FEN),
* 🤖 играть против шахматного движка **Stockfish** с ограниченной силой,
* 🧠 видеть **оценку позиции** в сантипешках,
* 🎯 использовать как **тренажёр для обучения шахматам**,
* 🌐 работать через **CLI** и **интерактивный Web-интерфейс (Streamlit)**.

Проект написан с упором на:

* чистую архитектуру (разделение логики и UI),
* читаемый код,
* пошаговое обучение (подходит для junior+/middle Python разработчиков, начинающих в ML и game-AI).

### Используемые технологии

* `python-chess`
* `Stockfish (UCI)`
* `Streamlit`
* Python 3.10+

---

## 🇬🇧 Description (English)

**Chess Helper** is an educational Python project for analyzing chess positions and playing against a chess engine at approximately 1000–1300 Elo strength.

The project allows you to:

* 🔍 get **top-N move suggestions** (MultiPV) for any position (FEN),
* 🤖 play against a **strength-limited Stockfish engine**,
* 🧠 see **position evaluations** in centipawns,
* 🎯 use it as a **chess training tool**,
* 🌐 run both via **CLI** and an **interactive Streamlit web UI**.

The project focuses on:

* clean architecture (engine logic separated from UI),
* readable and maintainable Python code,
* step-by-step learning (ideal for junior+/middle Python developers new to ML or game AI).

### Tech Stack

* `python-chess`
* `Stockfish (UCI)`
* `Streamlit`
* Python 3.10+

---

## 🚀 Quick start (optional block, если хочешь)

```bash
pip install python-chess streamlit
brew install stockfish
streamlit run ui_streamlit.py
```

