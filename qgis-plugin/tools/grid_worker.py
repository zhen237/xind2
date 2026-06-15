"""蜂窝拓扑异步计算 Worker"""
from PyQt5.QtCore import QObject, pyqtSignal


class GridWorker(QObject):
    progress = pyqtSignal(int, str)
    finished = pyqtSignal(list)
    error = pyqtSignal(str)

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

    def run(self):
        try:
            from design_engine.hex_grid import generate_hex_grid, generate_sites_from_grid

            isr = self.band_config.ideal_isr_km
            self.progress.emit(10, f"频段 {self.band_config.frequency_mhz}MHz, 站间距 {isr} km")

            grid_centers = generate_hex_grid(self.bbox, isr)
            self.progress.emit(30, f"生成网格点: {len(grid_centers)} 个")

            if self.avoidance_checker and self.avoidance_checker.avoidance_polygons:
                grid_centers = self.avoidance_checker.filter_valid_sites(grid_centers)
                self.progress.emit(45, f"避让过滤后: {len(grid_centers)} 个")

            sites = generate_sites_from_grid(
                grid_centers, self.band_config,
                site_type=self.site_type,
                tower_height=self.tower_height,
                num_sectors=self.num_sectors,
                existing_sites=self.existing_sites,
                bbox=self.bbox,
            )
            self.progress.emit(80, f"生成站点: {len(sites)} 个")

            self.finished.emit(sites)
        except Exception as e:
            self.error.emit(str(e))
