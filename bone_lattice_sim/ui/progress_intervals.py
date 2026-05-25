"""Независимые интервалы обновления GUI во время симуляции."""


def should_update_charts(step: int, every: int, time_steps: int) -> bool:
    """Обновить графики на шаге step (включая финальный шаг)."""
    every = max(1, every)
    return step % every == 0 or step >= time_steps


def should_record_animation_frame(step: int, every: int, time_steps: int) -> bool:
    """Сохранить кадр анимации на шаге step (включая финальный шаг)."""
    every = max(1, every)
    return step % every == 0 or step >= time_steps


def should_update_visual(step: int, every: int, time_steps: int) -> bool:
    """Отправить снимок для живого 3D на шаге step (включая финальный шаг)."""
    every = max(1, every)
    return step % every == 0 or step >= time_steps
