using TwinCsharp.Models;

namespace TwinCsharp.Services;

/// <summary>
/// 内存种子数据服务。当前无数据库，使用确定性种子数据，保证前端真实调用有返回。
/// 后续接入 M05 / MySQL 时，替换此类实现即可（接口不变）。
/// </summary>
public class InMemoryTwinDataService : ITwinDataService
{
    /// <summary>告警时间相对当前时间的偏移分钟数（模拟实时：3~52 分钟前）</summary>
    private static readonly int[] AlertTimeOffsets = { 3, 10, 17, 24, 31, 38, 45, 52 };

    private readonly List<Device> _devices;
    private readonly List<Alert> _alerts;

    public InMemoryTwinDataService()
    {
        _devices = SeedDevices();
        _alerts = SeedAlerts(_devices);
    }

    public List<Device> GetDevices() => _devices;

    public Device? GetDevice(string code) =>
        _devices.FirstOrDefault(d => d.DeviceCode == code);

    public List<Alert> GetAlerts()
    {
        // 模拟实时告警：每次请求把告警时间按固定偏移量映射到"当前时间的几分钟前"，
        // 使看板/告警列表呈现持续的实时感（告警内容与级别保持种子数据不变）。
        var now = DateTime.Now;
        for (var i = 0; i < _alerts.Count; i++)
        {
            _alerts[i].CreateTime = now.AddMinutes(-AlertTimeOffsets[i % AlertTimeOffsets.Length]);
        }
        return _alerts;
    }

    public DashboardDto GetDashboard()
    {
        var online = _devices.Count(d => d.Status == 1);
        var offline = _devices.Count(d => d.Status == 0);
        var fault = _devices.Count(d => d.Status == 2);
        var alertByLevel = new Dictionary<string, int>
        {
            ["提示"] = _alerts.Count(a => a.Level == 1),
            ["警告"] = _alerts.Count(a => a.Level == 2),
            ["严重"] = _alerts.Count(a => a.Level == 3)
        };
        var typeDist = _devices
            .GroupBy(d => d.DeviceType ?? "未知")
            .ToDictionary(g => g.Key, g => g.Count());

        return new DashboardDto
        {
            TotalDevices = _devices.Count,
            OnlineCount = online,
            OfflineCount = offline,
            FaultCount = fault,
            AlertTotal = _alerts.Count,
            AlertActive = _alerts.Count(a => a.Status == 0),
            AlertByLevel = alertByLevel,
            DeviceTypeDistribution = typeDist,
            RecentAlerts = GetAlerts().OrderByDescending(a => a.CreateTime).Take(5).ToList()
        };
    }

    private static List<Device> SeedDevices()
    {
        var baseTime = new DateTime(2026, 1, 1, 8, 0, 0);
        var rnd = new Random(20260831);
        var types = new[] { "塔吊", "升降机", "摄像头", "传感器", "配电箱" };
        var stations = new[] { "A区", "B区", "C区" };
        var list = new List<Device>();
        for (var i = 1; i <= 12; i++)
        {
            var status = i % 5 == 0 ? 2 : (i % 3 == 0 ? 0 : 1);
            var type = types[(i - 1) % types.Length];
            var code = $"DEV-{i:000}";
            list.Add(new Device
            {
                Id = i,
                DeviceCode = code,
                DeviceName = $"{type}-{i:000}",
                DeviceType = type,
                StationCode = stations[(i - 1) % stations.Length],
                InstallTime = baseTime.AddDays(i),
                Status = status,
                Manufacturer = "示范厂商",
                Model = $"X-{1000 + i}",
                CreateTime = baseTime.AddDays(i),
                Twin = new TwinState
                {
                    Temperature = Math.Round(20 + rnd.NextDouble() * 35, 1),
                    Load = Math.Round(rnd.NextDouble() * 100, 1),
                    RuntimeMinutes = (long)(rnd.NextDouble() * 50000),
                    LastSync = baseTime.AddMinutes(i * 37),
                    Health = status == 2 ? rnd.Next(10, 50) : rnd.Next(60, 99)
                }
            });
        }
        return list;
    }

    private static List<Alert> SeedAlerts(List<Device> devices)
    {
        var baseTime = new DateTime(2026, 8, 31, 9, 0, 0);
        var list = new List<Alert>();
        var contents = new[]
        {
            "塔吊力矩超限", "升降机门联锁异常", "摄像头离线", "传感器数据中断", "配电箱温度偏高"
        };
        for (var i = 1; i <= 8; i++)
        {
            var dev = devices[(i - 1) % devices.Count];
            list.Add(new Alert
            {
                Id = i,
                DeviceId = dev.Id,
                DeviceCode = dev.DeviceCode,
                AlertContent = contents[(i - 1) % contents.Length],
                Level = i % 4 == 0 ? 3 : (i % 2 == 0 ? 2 : 1),
                Status = i <= 5 ? 0 : 1,
                Source = "S5-施工监测",
                OrderNo = $"WO-{2026000 + i}",
                CreateTime = baseTime.AddHours(i),
                UpdateTime = i <= 5 ? null : baseTime.AddHours(i + 1)
            });
        }
        return list;
    }
}
