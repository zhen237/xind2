"""蜂窝拓扑异步计算 Worker — 使用 QThread 避免 UI 冻结"""
from PyQt5.QtCore import QObject, pyqtSignal, QThread


class GridWorkerSignals(QObject):
    """Worker 信号定义（独立 QObject 便于线程安全）"""
    progress = pyqtSignal(int, str)
    finished = pyqtSignal(list)
    error = pyqtSignal(str)


class GridWorker(QObject):
    """后台计算蜂窝拓扑 — 在 QThread 中运行避免阻塞 UI

    用法:
        thread = QThread()
        worker = GridWorker(bbox, config, ...)
        worker.moveToThread(thread)
        worker.signals.finished.connect(on_sites_ready)
        thread.started.connect(worker.run)
        thread.start()
    """

    def __init__(self, bbox, band_config, site_type, tower_height,
                 num_sectors, scenario, existing_sites, avoidance_checker):
        super().__init__()
        self.bbox = bbox
        self.band_config = band_config
        self.site_type = site_type
        self.tower_height = tower_height
        self.num_sectors = num_sectors
        self.scenario = scenario
        self.existing_sites = existing_sites
        self.avoidance_checker = avoidance_checker
        self.signals = GridWorkerSignals()
        self._is_cancelled = False

    def cancel(self):
        """请求取消计算"""
        self._is_cancelled = True

    def run(self):
        """在后台线程中执行（由 QThread.started 触发）"""
        try:
            from design_engine.hex_grid import generate_hex_grid, generate_sites_from_grid

            isr = self.band_config.ideal_isr_km
            self.signals.progress.emit(10, f"频段 {self.band_config.frequency_mhz}MHz, 站间距 {isr} km")

            if self._is_cancelled:
                return

            grid_centers = generate_hex_grid(self.bbox, isr)
            self.signals.progress.emit(30, f"生成网格点: {len(grid_centers)} 个")

            if self._is_cancelled:
                return

            if self.avoidance_checker and self.avoidance_checker.avoidance_polygons:
                grid_centers = self.avoidance_checker.filter_valid_sites(grid_centers)
                self.signals.progress.emit(45, f"避让过滤后: {len(grid_centers)} 个")

            if self._is_cancelled:
                return

            # 截断超过200个站点
            if len(grid_centers) > 200:
                grid_centers = grid_centers[:200]

            sites = generate_sites_from_grid(
                grid_centers, self.band_config,
                site_type=self.site_type,
                tower_height=self.tower_height,
                num_sectors=self.num_sectors,
                existing_sites=self.existing_sites,
                bbox=self.bbox,
            )
            self.signals.progress.emit(85, f"生成站点: {len(sites)} 个")

            self.signals.finished.emit(sites)
        except Exception as e:
            self.signals.error.emit(str(e))
