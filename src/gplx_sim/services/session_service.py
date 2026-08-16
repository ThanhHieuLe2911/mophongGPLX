from __future__ import annotations

from dataclasses import dataclass, field

from gplx_sim.domain.models import Situation, SituationResult
from gplx_sim.domain.scoring import grade_situation, score_on_ten
from gplx_sim.repositories.history_repository import HistoryRepository


@dataclass(slots=True)
class SessionState:
    session_id: int
    mode: str
    situations: list[Situation]
    current_index: int = 0
    results: list[SituationResult] = field(default_factory=list)

    @property
    def current(self) -> Situation:
        return self.situations[self.current_index]

    @property
    def is_last(self) -> bool:
        return self.current_index == len(self.situations) - 1

    def submit_current(self, selections: dict[int, int]) -> SituationResult:
        result = grade_situation(self.current, selections)
        self.results = [item for item in self.results if item.situation_id != result.situation_id]
        self.results.append(result)
        return result

    def complete_unanswered(self) -> None:
        """Chấm các tình huống chưa nộp là 0 điểm khi hết giờ."""
        completed_ids = {result.situation_id for result in self.results}
        for situation in self.situations:
            if situation.id not in completed_ids:
                self.results.append(grade_situation(situation, {}))

    def move_next(self) -> bool:
        if self.is_last:
            return False
        self.current_index += 1
        return True

    def move_to(self, index: int) -> None:
        if not 0 <= index < len(self.situations):
            raise IndexError("Vị trí tình huống nằm ngoài phiên làm bài")
        self.current_index = index

    def finish(self, history: HistoryRepository) -> float:
        self.complete_unanswered()
        final_score = score_on_ten(self.results, len(self.situations))
        history.complete_session(
            self.session_id,
            self.situations,
            self.results,
            final_score,
        )
        return final_score
