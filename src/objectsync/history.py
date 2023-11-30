from typing import Dict, List
import logging
logger = logging.getLogger(__name__)
from topicsync import Transition

class HistoryItem:
    def __init__(self, transition: Transition, done: bool = False):
        self.transition = transition
        self.done = done

class History:
    def __init__(self,max_len=1000) -> None:
        self.chain:List[HistoryItem] = []
        self._current_index = -1
        self.max_len = max_len

    def add(self, transition: Transition):
        # Prune unreachable chain
        self.chain = self.chain[:self._current_index+1]
        self.chain.append(HistoryItem(transition,done=True))
        self._current_index += 1
        if len(self.chain) > self.max_len:
            self.chain = self.chain[1:]
            self._current_index -= 1

    def clear(self):
        # This is used when some change is made that invalidates the history, in other words, some not undoable change.
        self.chain = []
        self._current_index = -1

    def undo(self) -> Transition|None:
        if self._current_index >= 0:
            self.chain[self._current_index].done = False
            self._current_index -= 1

            debug_msg = '\n=== undo ===\n'
            for change in reversed(self.chain[self._current_index+1].transition.changes):
                debug_msg += str(change.serialize()) + '\n'
            debug_msg += '\n'
            logger.debug(debug_msg)

            return self.chain[self._current_index+1].transition
        else:
            return None
        
    def redo(self) -> Transition|None:
        if self._current_index < len(self.chain)-1:
            self._current_index += 1
            self.chain[self._current_index].done = True

            debug_msg = '\n=== redo ===\n'
            for change in self.chain[self._current_index].transition.changes:
                debug_msg += str(change.serialize()) + '\n'
            debug_msg += '\n'
            logger.debug(debug_msg)

            return self.chain[self._current_index].transition
        else:
            return None

