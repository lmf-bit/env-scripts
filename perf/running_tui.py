from textual.app import App, ComposeResult
from textual.coordinate import Coordinate
from textual.widgets import Static, Footer, Header, DataTable
from textual.containers import ScrollableContainer
from textual.reactive import reactive
import random
import time

list_data_ext = [[f"Item {r}{c}" for c in range(15)] for r in range(100)]

class DynamicList(Static):
    global list_data_ext
    table = DataTable()

    def on_mount(self) -> None:
        self.update_timer = self.set_interval(1, self.update_list_data)
        self.table.add_columns(*list_data_ext[0])
        self.table.add_rows(list_data_ext[1:])
        self.mount(self.table)

    def update_list_data(self) -> None:
        for r, row in enumerate(list_data_ext):
            for c, value in enumerate(row):
                if r < len(self.table.rows) and c < len(self.table.columns):
                    self.table.update_cell_at((r, c), value)

class RunningTuiApp(App):
    """A Textual app to manage running cases."""

    BINDINGS = [("d", "toggle_dark", "Toggle dark mode")]

    def compose(self) -> ComposeResult:
        """Create child widgets for the app."""
        yield Header()
        yield Footer()
        yield ScrollableContainer(DynamicList())

    def action_toggle_dark(self) -> None:
        """An action to toggle dark mode."""
        self.dark = not self.dark


def update():
    global list_data_ext
    while True:
        list_data_ext = [[f"Item {random.randint(0, r)}{c}" for c in range(15)] for r in range(100)]
        time.sleep(1)

if __name__ == "__main__":
    import threading
    job = threading.Thread(target=update)
    app = RunningTuiApp()
    job.start()
    app.run()
