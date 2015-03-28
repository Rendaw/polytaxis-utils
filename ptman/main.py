import sys
import shlex

class QueryAgg():
    def __init__(self):
        self.entry = QLineEdit()
        self.entry.returnPressed.connect(self.submit)
        self.query_changed = pyqtSignal(set, set, list, list)

    def root(self):
        return self.entry

    def submit(self):
        includes = set()
        excludes = set()
        columns = []
        sort = []
        includes, excludes, sort, columns = parse_query(
            shlex.split(self.entry.getText())
        )
        self.query_changed.emit(includes, excludes, sort, columns)

class ResultAgg():
    def __init__(self):
        class Model(QAbstractTableModel):
            def rowCount(self, index):
                pass

            def canFetchMore(self, index):
                pass

            def fetchMore(self, index):
                pass
        self.table = QListWidget()

    def root(self):
        return self.table

    def pane(self):
        return self.info

class QueryWorker(QObject):
    def __init__(self):
        super(QueryWorker, self).__init__()
        self.conn = ptmon.common.open_db()
        self.signal_found = pyqtSignal(tuple)

    @pyqtSlot(set, set, list, list)
    def handle_query(include, exclude, sort, columns):
        primary_count = 1
        include_primary = []
        for key, value in include.items():
            include_primary.append(polytaxis.encode_tag(key, value))
            if len(include_primary) >= primary_count:
                break
        for fid in self.conn.execute(
                'SELECT file FROM tags WHERE tag = :tag',
                {
                    'tag': polytaxis.encode_tag(include_primary[0]),
                },
                ):
            fid = fid[0]
            segment, tags = self.conn.execute(
                'SELECT * FROM files WHERE id = :fid LIMIT 1',
                {
                    'fid': fid,
                },
            ).fetchone()
            tags = polytaxis.decode_tags(tags)
            def manual_filter():
                for key, value in include.items():
                    found_values = tags.get(key)
                    if found_values is None:
                        return False
                    if not value in found_values:
                        return False
                for key, value in exclude.items():
                    found_values = tags.get(key)
                    if found_values is not None:
                        return False
                    if value in found_values:
                        return False
                return True
            if not manual_filter():
                continue
            self.signal_found.emit((fid, segment, tags))
            

def main():
    app = QApplication(sys.argv)

    # Start thread/worker
    thread = QThread()
    worker = QueryWorker()
    worker.moveToThread(thread)
    
    # Build the interface
    main_layout = QVBoxLayout()
    query = QueryAgg()
    main_layout.addWidget(query.root())
    results = ResultAgg()
    main_layout.addWidget(results.root())
    toolbar = QToolbar()
    settings = toolbar.addAction('settings')
    toolbar_space = QWidget()
    toolbar.addWidget(toolbar_space)
    all_tags = toolbar.addAction('tags')
    all_open = toolbar.addAction('open all')
    toggle_info = toolbar.addAction('toggle info')
    main_layout.addWidget(toolbar)
    
    window_layout = QHBoxLayout()
    window_layout.addLayout(main_layout)
    window_layout.addWidget(results.pane())
    
    window = QWidget()
    window.setLayout(window_layout)
    window.show()
    
    # Connect everything
    toggle_info.triggered.connect(
        lambda i: results.pane().setVisible(not results.pane().isVisible())
    )

    sys.exit(app.exec_())
