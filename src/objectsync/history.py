from typing import Dict, List
from chatroom import Transition

class HistoryItem:
    def __init__(self, transition: Transition, done: bool = False):
        self.transition = transition
        self.done = done

class History:
    def __init__(self) -> None:
        self.chain:List[HistoryItem] = []
        self._current_index = -1

    def add(self, transition: Transition):
        # Prune unreachable chain
        self.chain = self.chain[:self._current_index+1]
        self.chain.append(HistoryItem(transition,done=True))
        self._current_index += 1

    def undo(self) -> Transition|None:
        if self._current_index >= 0:
            self.chain[self._current_index].done = False
            self._current_index -= 1

            print('\n=== undo ===')
            for change in reversed(self.chain[self._current_index+1].transition.changes):
                print(change.serialize())
            print('')
            return self.chain[self._current_index+1].transition
        else:
            return None
        
    def redo(self) -> Transition|None:
        if self._current_index < len(self.chain)-1:
            self._current_index += 1
            self.chain[self._current_index].done = True

            print('\n=== redo ===')
            for change in self.chain[self._current_index].transition.changes:
                print(change.serialize())
            print('')
            return self.chain[self._current_index].transition
        else:
            return None

